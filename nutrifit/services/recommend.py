from datetime import datetime, timedelta, timezone
from collections import defaultdict
import math
import random
import re
from types import SimpleNamespace

from sqlalchemy import func

from ..models import (
    CatalogFood,
    CatalogWorkout,
    FoodLog,
    UserProfile,
    WorkoutLog,
)

ACTIVITY_MULTIPLIER = {
    "low": 1.2,
    "moderate": 1.45,
    "high": 1.65,
}

GOAL_ADJUSTMENT = {
    "cut": -300,
    "balance": 0,
    "gain_muscle": 250,
}


def _today_range():
    now = datetime.now().astimezone()
    start_local = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc


def _estimate_calories(profile) -> float:
    if not all(
        getattr(profile, field, None)
        for field in ("sex", "age", "height_cm", "weight_kg")
    ):
        return profile.goal_kcal or 2000

    weight = float(profile.weight_kg)
    height = float(profile.height_cm)
    age = float(profile.age)
    if profile.sex == "female":
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age + 5

    multiplier = ACTIVITY_MULTIPLIER.get(profile.activity_level or "", 1.4)
    base = bmr * multiplier
    adj = GOAL_ADJUSTMENT.get(profile.goal_type or "balance", 0)
    exercise_minutes = float(getattr(profile, "exercise_minutes", 0) or 0)
    # Rough calorie bonus: assume 6 METs (조깅)로 계산
    exercise_bonus = exercise_minutes * weight * 0.0175 * 6
    return profile.goal_kcal or base + adj + exercise_bonus


def _goal_targets(profile: UserProfile | SimpleNamespace) -> dict:
    goal_kcal = _estimate_calories(profile)
    protein = goal_kcal * 0.25 / 4
    fat = goal_kcal * 0.25 / 9
    carb = goal_kcal * 0.50 / 4
    return {
        "kcal": goal_kcal,
        "protein_g": protein,
        "fat_g": fat,
        "carb_g": carb,
    }


def _profile_metrics(profile):
    try:
        age = float(profile.age) if profile.age is not None else None
    except (TypeError, ValueError):
        age = None
    try:
        height_m = float(profile.height_cm) / 100 if profile.height_cm else None
        weight = float(profile.weight_kg) if profile.weight_kg else None
        bmi = weight / (height_m ** 2) if weight and height_m else None
    except (TypeError, ValueError, ZeroDivisionError):
        height_m = weight = bmi = None
    return {
        "age": age,
        "bmi": bmi,
        "sex": getattr(profile, "sex", None),
        "goal": getattr(profile, "goal_type", "balance") or "balance",
    }


def dashboard(user_id: str) -> dict | None:
    user = UserProfile.query.get(user_id)
    if not user:
        return None

    target = _goal_targets(user)
    start, end = _today_range()

    totals = (
        FoodLog.query.with_entities(
            func.coalesce(func.sum(FoodLog.kcal), 0),
            func.coalesce(func.sum(FoodLog.protein_g), 0),
            func.coalesce(func.sum(FoodLog.fat_g), 0),
            func.coalesce(func.sum(FoodLog.carb_g), 0),
        )
        .filter(FoodLog.user_id == user_id, FoodLog.ts >= start, FoodLog.ts < end)
        .first()
    )
    eaten = {
        "kcal": totals[0],
        "protein_g": totals[1],
        "fat_g": totals[2],
        "carb_g": totals[3],
    }

    burn = (
        WorkoutLog.query.with_entities(
            func.coalesce(func.sum(WorkoutLog.kcal_burn), 0)
        )
        .filter(WorkoutLog.user_id == user_id, WorkoutLog.ts >= start, WorkoutLog.ts < end)
        .scalar()
        or 0
    )

    remain = {
        "kcal": max(target["kcal"] - eaten["kcal"] + 0.7 * burn, 0),
        "protein_g": max(target["protein_g"] - eaten["protein_g"], 0),
        "fat_g": max(target["fat_g"] - eaten["fat_g"], 0),
        "carb_g": max(target["carb_g"] - eaten["carb_g"], 0),
    }

    return {"target": target, "eaten": eaten, "burn": burn, "remain": remain}


def recommend_foods(
    user_id: str, topn: int = 3, exclude_names: list[str] | None = None
):
    profile = UserProfile.query.get(user_id)
    dash = dashboard(user_id)
    if not dash or not profile:
        return {"items": [], "meals": []}

    rng = random.Random(datetime.utcnow().timestamp())

    remain = dash["remain"]
    remain = {k: float(remain.get(k, 0) or 0.0) for k in remain}
    candidates = CatalogFood.query.all()
    if not candidates:
        return {"items": [], "meals": []}

    goal_type = (profile.goal_type or "balance").lower()
    metrics = _profile_metrics(profile)
    bmi = metrics["bmi"] or 22
    sex = (metrics["sex"] or "").lower()
    activity_level = (profile.activity_level or "moderate").lower()

    protein_bias = 1.5 if goal_type == "gain_muscle" else 1.0
    fat_bias = 1.3 if goal_type == "cut" or bmi > 27 else 1.0
    carb_bias = 1.2 if goal_type == "balance" else 1.0
    if bmi < 20:
        carb_bias += 0.4

    goal_preferences = {
        "cut": {
            "calorie_weight": 1.3,
            "density_weight": 1.4,
            "protein_emphasis": 1.2,
            "fat_emphasis": 1.3,
            "carb_emphasis": 1.0,
            "meal_split": (0.35, 0.4, 0.25),
        },
        "gain_muscle": {
            "calorie_weight": 0.85,
            "density_weight": 0.7,
            "protein_emphasis": 1.8,
            "fat_emphasis": 0.9,
            "carb_emphasis": 1.05,
            "meal_split": (0.3, 0.45, 0.25),
        },
        "balance": {
            "calorie_weight": 1.0,
            "density_weight": 1.0,
            "protein_emphasis": 1.1,
            "fat_emphasis": 1.0,
            "carb_emphasis": 1.1,
            "meal_split": (0.3, 0.4, 0.3),
        },
    }
    pref = goal_preferences.get(goal_type, goal_preferences["balance"])
    protein_bias *= pref["protein_emphasis"]
    fat_bias *= pref["fat_emphasis"]
    carb_bias *= pref["carb_emphasis"]

    estimated_kcal = _estimate_calories(profile)
    sex_appetite = 1.05 if sex == "male" else 0.97 if sex == "female" else 1.0
    activity_appetite = {"low": 0.95, "moderate": 1.0, "high": 1.1}.get(
        activity_level, 1.0
    )
    portion_factor = max(estimated_kcal / 2000.0, 0.7) * sex_appetite * activity_appetite
    if bmi > 27:
        portion_factor *= 0.85

    macro_fields = ("protein_g", "fat_g", "carb_g")

    def _macro(value):
        if value is None:
            return 0.0
        try:
            val = float(value)
        except (TypeError, ValueError):
            return 0.0
        if math.isnan(val):
            return 0.0
        return val

    def _is_plausible_food(food: CatalogFood) -> bool:
        kcal = _macro(food.kcal)
        macros = {
            "protein_g": _macro(food.protein_g),
            "fat_g": _macro(food.fat_g),
            "carb_g": _macro(food.carb_g),
        }
        total_macro = sum(macros.values())
        est_kcal = 4 * (macros["protein_g"] + macros["carb_g"]) + 9 * macros["fat_g"]
        if est_kcal <= 0 and kcal <= 0:
            return False
        ratio = kcal / max(est_kcal, 1.0)
        if est_kcal > 0 and (ratio < 0.3 or ratio > 2.5):
            return False
        if kcal < 20 and total_macro < 8:
            return False
        return True

    candidates = [item for item in candidates if _is_plausible_food(item)]

    def _normalize_name(name: str) -> str:
        if not name:
            return ""
        base = re.sub(r"\(.*?\)", "", name)
        base = base.replace("_", " ")
        return re.sub(r"\s+", " ", base).strip().lower()

    def _coarse_key(name: str) -> str:
        norm = _normalize_name(name)
        if not norm:
            return ""
        tokens = [tok for tok in re.split(r"[\s/]+", norm) if tok]
        if not tokens:
            return norm
        first = tokens[0]
        if len(first) <= 1 and len(tokens) > 1:
            first = first + tokens[1]
        return first

    def _food_type(food: CatalogFood) -> str:
        tags = (food.tags or "").lower()
        name = (food.name or "").lower()
        processed_keywords = (
            "가공",
            "음료",
            "차",
            "티",
            "주스",
            "캔디",
            "젤리",
            "바 ",
            "바-",
            "스낵",
            "보충",
            "음료수",
        )
        if any(keyword in tags for keyword in ("가공식품", "가공", "음료", "보충제", "간식")):
            return "processed"
        if any(keyword in name for keyword in processed_keywords):
            return "processed"
        return "natural"

    def _quality_penalty(food_macros: dict, kcal: float) -> float:
        est_kcal = (
            4 * (food_macros["protein_g"] + food_macros["carb_g"])
            + 9 * food_macros["fat_g"]
        )
        if est_kcal <= 0:
            return 15.0
        ratio = kcal / max(est_kcal, 1.0)
        if ratio < 0.4:
            return (0.4 - ratio) * 60
        if ratio > 1.8:
            return (ratio - 1.8) * 15
        return 0.0

    def rank_for_needs(needs: dict):
        macro_needs = {
            field: max(needs.get(field, 0.0), 0.0) for field in macro_fields
        }
        macro_normalizer = len([f for f, need in macro_needs.items() if need > 0]) or len(
            macro_fields
        )
        calorie_budget = max(needs.get("kcal", 0.0), 0.0)
        calorie_floor = max(
            calorie_budget, estimated_kcal * 0.05 * sex_appetite * activity_appetite
        )

        min_kcal_required = (
            max(70.0, calorie_budget * 0.18) if calorie_budget >= 180 else 0.0
        )

        def score(food: CatalogFood):
            kcal = _macro(food.kcal)
            food_macros = {
                "protein_g": _macro(food.protein_g),
                "fat_g": _macro(food.fat_g),
                "carb_g": _macro(food.carb_g),
            }
            if calorie_budget > 0:
                kcal_penalty = (
                    max(kcal - calorie_budget, 0) * 2 / portion_factor
                ) * pref["calorie_weight"]
            else:
                kcal_penalty = (kcal / calorie_floor) * 4 * pref["calorie_weight"]

            if min_kcal_required and kcal < min_kcal_required:
                kcal_penalty += (min_kcal_required - kcal) * 0.4

            macro_penalty = 0.0
            coverage = 0.0
            density_reward = 0.0
            for field in macro_fields:
                need = macro_needs[field]
                have = food_macros[field]
                bias = {
                    "protein_g": protein_bias,
                    "fat_g": fat_bias,
                    "carb_g": carb_bias,
                }[field]
                if need <= 0:
                    macro_penalty += have * 0.05 * bias
                    continue
                diff_ratio = abs(have - need) / max(need, 1.0)
                macro_penalty += diff_ratio**2 * bias
                coverage += min(have, need) / max(need, 1.0)
                if kcal > 0:
                    density_reward += (min(have, need) / max(kcal, 1)) * bias

            coverage_gap = max(1 - (coverage / macro_normalizer), 0.0)
            quality_pen = _quality_penalty(food_macros, kcal)
            return (
                kcal_penalty * 0.6
                + macro_penalty * 8
                + coverage_gap * 5
                - density_reward
                * (25 if calorie_budget <= 0 else 6)
                * pref["density_weight"]
                + quality_pen
            )

        return sorted(candidates, key=score)

    def serialize_food(food: CatalogFood):
        return {
            "name": food.name,
            "kcal": _macro(food.kcal),
            "protein_g": _macro(food.protein_g),
            "fat_g": _macro(food.fat_g),
            "carb_g": _macro(food.carb_g),
            "tags": food.tags,
            "food_type": _food_type(food),
        }

    meal_split = list(pref["meal_split"])
    if sex == "male":
        meal_split[0] -= 0.04
        meal_split[1] += 0.025
        meal_split[2] += 0.015
    elif sex == "female":
        meal_split[0] += 0.02
        meal_split[2] -= 0.02
    if activity_level == "high":
        meal_split[1] += 0.03
        meal_split[2] += 0.02
        meal_split[0] -= 0.05
    elif activity_level == "low":
        meal_split[0] += 0.03
        meal_split[2] -= 0.03

    meal_split = [max(0.15, ratio) for ratio in meal_split]
    total_ratio = sum(meal_split)
    meal_split = [ratio / total_ratio for ratio in meal_split]

    MEAL_SPLIT = [
        ("breakfast", {"label": "아침", "ratio": meal_split[0]}),
        ("lunch", {"label": "점심", "ratio": meal_split[1]}),
        ("dinner", {"label": "저녁", "ratio": meal_split[2]}),
    ]

    meals = []
    flat_items = []
    exclude_norms = {
        _normalize_name(name) for name in (exclude_names or []) if name.strip()
    }
    used_names = set(exclude_norms)
    used_groups = defaultdict(int)
    for name in (exclude_names or []):
        key = _coarse_key(name)
        if key:
            used_groups[key] = 1

    for key, meta in MEAL_SPLIT:
        portion = meta["ratio"]
        targets = {
            nutrient: max(remain.get(nutrient, 0.0), 0.0) * portion
            for nutrient in ("kcal", "protein_g", "fat_g", "carb_g")
        }
        ranked = rank_for_needs(targets)
        pool_limit = max(topn + 12, topn * 4)
        top_pool = ranked[:pool_limit]
        random_pool = top_pool[:]
        rng.shuffle(random_pool)

        meal_items = []
        meal_norms = set()
        meal_groups = set()

        def _can_use(food: CatalogFood) -> bool:
            norm = _normalize_name(food.name)
            if not norm:
                return False
            if norm in used_names or norm in meal_norms:
                return False
            coarse = _coarse_key(food.name)
            if coarse:
                limit = 1
                if used_groups.get(coarse, 0) >= limit or coarse in meal_groups:
                    return False
            return True

        def _take(food: CatalogFood):
            norm = _normalize_name(food.name)
            meal_items.append(serialize_food(food))
            used_names.add(norm)
            meal_norms.add(norm)
            coarse = _coarse_key(food.name)
            if coarse:
                used_groups[coarse] += 1
                meal_groups.add(coarse)

        def _pick_from(source: list[CatalogFood], category: str | None = None) -> bool:
            for food in source:
                if len(meal_items) >= topn:
                    return False
                if category and _food_type(food) != category:
                    continue
                if not _can_use(food):
                    continue
                _take(food)
                return True
            return False

        def _ensure_category(category: str):
            if len(meal_items) >= topn:
                return
            has_available = any(
                _food_type(food) == category and _can_use(food) for food in ranked
            )
            if not has_available:
                return
            if _pick_from(top_pool, category):
                return
            _pick_from(ranked, category)

        _ensure_category("natural")
        _ensure_category("processed")

        if len(meal_items) < topn:
            _pick_from(random_pool)

        if len(meal_items) < topn:
            _pick_from(ranked)
        meals.append(
            {
                "key": key,
                "label": meta["label"],
                "ratio": portion,
                "targets": targets,
                "items": meal_items,
            }
        )
        flat_items.extend(meal_items)

    return {"meals": meals, "items": flat_items}


def auto_goal_plan(data: dict) -> dict:
    """Recommend goal calories/macros from raw profile data."""
    required = ["sex", "age", "height_cm", "weight_kg"]
    missing = [field for field in required if not data.get(field)]
    if missing:
        raise ValueError(f"{', '.join(missing)} 값이 필요합니다.")

    try:
        profile_stub = SimpleNamespace(
            sex=data.get("sex"),
            age=int(float(data.get("age"))),
            height_cm=float(data.get("height_cm")),
            weight_kg=float(data.get("weight_kg")),
            activity_level=data.get("activity_level") or "moderate",
            goal_type=data.get("goal_type") or "balance",
            goal_kcal=None,
            exercise_minutes=float(data.get("exercise_minutes") or data.get("minutes") or 0),
        )
    except (TypeError, ValueError):
        raise ValueError("나이/키/몸무게는 숫자여야 합니다.")

    targets = _goal_targets(profile_stub)
    return {
        "goal_kcal": targets["kcal"],
        "protein_g": targets["protein_g"],
        "fat_g": targets["fat_g"],
        "carb_g": targets["carb_g"],
    }


def recommend_workouts(
    user_id: str, topn: int = 3, minutes: int = 20, exclude_names: list[str] | None = None
):
    profile = UserProfile.query.get(user_id)
    dash = dashboard(user_id)
    if not dash or not profile:
        return {"items": [], "requested_minutes": minutes, "assigned_minutes": 0}

    rng = random.Random(datetime.utcnow().timestamp())

    remain_kcal = dash["remain"]["kcal"]
    candidates = CatalogWorkout.query.all()
    all_workouts = list(candidates)
    weight = float(profile.weight_kg or 65)
    goal_type = profile.goal_type or "balance"
    metrics = _profile_metrics(profile)
    age = metrics["age"] or 35
    bmi = metrics["bmi"] or 23
    sex = (metrics["sex"] or "").lower()

    def _normalize_name(name: str) -> str:
        if not name:
            return ""
        return re.sub(r"\s+", " ", name.strip().lower())

    excluded = {_normalize_name(name) for name in (exclude_names or []) if name}
    primary_pool = [w for w in all_workouts if _normalize_name(w.name) not in excluded]
    if len(primary_pool) < topn:
        primary_pool = list(all_workouts)
        excluded.clear()
    fallback_pool = list(all_workouts)
    used_norms = set()

    def preferred_met_range():
        low, high = 3.0, 6.0
        if sex == "male":
            high += 1.5
        else:
            high += 0.5
        if age < 30:
            high += 1.0
        if age > 50:
            high -= 1.0
            low -= 0.5
        if bmi > 27:
            low = max(low, 3.5)
            high = min(high + 0.5, 8.0)
        elif bmi < 20:
            low = max(2.0, low - 0.3)
            high += 0.8
        if goal_type == "cut":
            low = max(low, 4.0)
            high = max(high, 8.0)
        if goal_type == "gain_muscle":
            low = max(low, 3.0)
            high = max(high, 7.0)
        return (max(1.5, low), min(high, 12.0))

    met_low, met_high = preferred_met_range()

    CATEGORY_PLAN = {
        "cut": ["cardio", "strength", "lifestyle", "cardio", "stretch"],
        "balance": ["cardio", "strength", "stretch", "lifestyle"],
        "gain_muscle": ["strength", "cardio", "strength", "stretch"],
    }

    category_sequence = CATEGORY_PLAN.get(goal_type, CATEGORY_PLAN["balance"]).copy()
    if bmi > 27:
        category_sequence = ["cardio", "cardio", "lifestyle", "strength", "stretch"]
    elif bmi < 20:
        category_sequence = ["strength", "cardio", "strength", "stretch", "lifestyle"]
    if sex == "female":
        category_sequence.insert(2, "stretch")
    if metrics["age"] and metrics["age"] > 55:
        category_sequence.append("lifestyle")

    def intensity_bias(category: str, mets: float) -> float:
        if goal_type == "gain_muscle" and category == "strength":
            return 0.7
        if goal_type == "cut" and category in {"cardio", "lifestyle"}:
            return 0.7
        if bmi > 27 and category == "strength":
            return 1.2
        if bmi < 20 and category == "cardio":
            return 1.3
        if mets > met_high + 2:
            return 1.5
        return 1.0

    def score(workout: CatalogWorkout, remain_minutes: int, remain_kcal_value: float):
        est_minutes = min(workout.max_minutes or remain_minutes, remain_minutes)
        est_minutes = max(est_minutes, workout.min_minutes or 10)
        est_burn = workout.mets * weight * 0.0175 * est_minutes
        burn_gap = abs(remain_kcal_value - est_burn)
        # 짧지만 필요한 시간과 가까운 운동을 약간 우대
        time_gap = abs(est_minutes - remain_minutes)
        if workout.mets < met_low:
            intensity_penalty = (met_low - workout.mets) ** 2
        elif workout.mets > met_high:
            intensity_penalty = (workout.mets - met_high) ** 2
        else:
            intensity_penalty = 0
        return (
            burn_gap
            + time_gap * 4 * intensity_bias(workout.category, workout.mets)
            + intensity_penalty * 8
        )
    remaining = minutes
    selected = []

    MIN_SLOT_MINUTES = 10

    def _remove_from_pools(workout):
        if workout in primary_pool:
            primary_pool.remove(workout)
        if workout in fallback_pool:
            fallback_pool.remove(workout)

    def _can_use(workout, allow_excluded=False):
        norm = _normalize_name(workout.name)
        if not norm:
            return False
        if norm in used_norms:
            return False
        if not allow_excluded and norm in excluded:
            return False
        return True

    def _get_pool(category: str | None, allow_excluded=False):
        sources = [primary_pool, fallback_pool]
        for source in sources:
            filtered = [
                w
                for w in source
                if (category is None or w.category == category)
                and _can_use(w, allow_excluded)
            ]
            if filtered:
                return filtered
        return []

    while fallback_pool and remaining > 0 and len(selected) < topn:
        desired_category = category_sequence[len(selected) % len(category_sequence)]
        pool = _get_pool(desired_category, allow_excluded=False)
        if not pool:
            pool = _get_pool(None, allow_excluded=False)
        if not pool:
            pool = _get_pool(desired_category, allow_excluded=True)
        if not pool:
            pool = _get_pool(None, allow_excluded=True)
        if not pool:
            break

        pool.sort(key=lambda w: score(w, remaining, remain_kcal))
        slice_size = max(1, min(3, len(pool)))
        choice_pool = pool[:slice_size]
        workout = rng.choice(choice_pool)
        _remove_from_pools(workout)

        min_min = workout.min_minutes or 10
        max_min = workout.max_minutes or min_min
        if min_min > max_min:
            max_min = min_min

        remaining_slots = max(topn - len(selected) - 1, 0)
        reserve = remaining_slots * MIN_SLOT_MINUTES

        if remaining <= min_min or (not selected and remaining < min_min):
            assign = remaining
        else:
            if remaining > reserve:
                max_allow = remaining - reserve
            else:
                max_allow = remaining
            max_allow = min(max_allow, max_min)
            assign = max(min_min, max_allow)
            assign = min(assign, remaining)
        if assign <= 0:
            continue

        selected.append(
            {
                "name": workout.name,
                "mets": workout.mets,
                "category": workout.category,
                "suggested_minutes": assign,
                "min_minutes": min_min,
                "max_minutes": max_min,
                "per_min_kcal": workout.mets * weight * 1.05 / 60.0,
                "total_kcal": workout.mets * weight * 1.05 * (assign / 60.0),
            }
        )
        remaining -= assign
        used_norms.add(_normalize_name(workout.name))

    # distribute leftover minutes if any
    if remaining > 0 and selected:
        for item in selected:
            available = item["max_minutes"] - item["suggested_minutes"]
            if available <= 0:
                continue
            add = min(available, remaining)
            item["suggested_minutes"] += add
            remaining -= add
            if remaining <= 0:
                break

    total_assigned = sum(item["suggested_minutes"] for item in selected)

    # Cleanup metadata not needed by client
    for item in selected:
        item.pop("min_minutes", None)
        item.pop("max_minutes", None)

    return {
        "items": selected,
        "requested_minutes": minutes,
        "assigned_minutes": total_assigned,
        "unfilled_minutes": max(minutes - total_assigned, 0),
    }


def _utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _local_date(dt: datetime) -> datetime.date:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone().date()


def weekly_report(user_id: str, days: int = 7) -> dict | None:
    user = UserProfile.query.get(user_id)
    if not user:
        return None

    now_local = datetime.now().astimezone()
    start_local = now_local - timedelta(days=days)
    start_utc = _utc_naive(start_local)

    food_logs = (
        FoodLog.query.with_entities(FoodLog.ts, FoodLog.kcal)
        .filter(FoodLog.user_id == user_id, FoodLog.ts >= start_utc)
        .all()
    )

    workout_logs = (
        WorkoutLog.query.with_entities(WorkoutLog.ts, WorkoutLog.kcal_burn)
        .filter(WorkoutLog.user_id == user_id, WorkoutLog.ts >= start_utc)
        .all()
    )

    food_map: dict[str, float] = {}
    for ts, kcal in food_logs:
        key = str(_local_date(ts))
        food_map[key] = food_map.get(key, 0.0) + float(kcal or 0)

    workout_map: dict[str, float] = {}
    for ts, kcal in workout_logs:
        key = str(_local_date(ts))
        workout_map[key] = workout_map.get(key, 0.0) + float(kcal or 0)

    days_list = []
    target = _goal_targets(user)["kcal"]
    compliance = []
    for i in range(days - 1, -1, -1):
        day = (now_local - timedelta(days=i)).date()
        day_str = str(day)
        eat = food_map.get(day_str, 0.0)
        burn = workout_map.get(day_str, 0.0)
        gap = target - eat + burn
        days_list.append(
            {
                "date": day_str,
                "eat": round(eat),
                "burn": round(burn),
                "gap": round(gap),
            }
        )
        compliance.append(1 if abs(gap) <= target * 0.1 else 0)

    summary = {
        "avg_eat": round(sum(d["eat"] for d in days_list) / days, 1) if days_list else 0,
        "avg_burn": round(sum(d["burn"] for d in days_list) / days, 1) if days_list else 0,
        "max_eat": max((d["eat"] for d in days_list), default=0),
        "min_eat": min((d["eat"] for d in days_list), default=0),
        "compliance": round(sum(compliance) / len(compliance) * 100, 1) if compliance else 0,
    }

    return {"days": days_list, "summary": summary, "target": round(target)}
