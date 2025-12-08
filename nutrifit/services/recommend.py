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


def recommend_foods(
    user_id: str, topn: int = 3, exclude_names: list[str] | None = None
):
    profile = UserProfile.query.get(user_id)
    dash = dashboard(user_id)
    if not dash or not profile:
        return {"items": [], "meals": []}

    rng = random.Random(datetime.utcnow().timestamp())
    remain = dash["remain"]
    remain_kcal = float(remain.get("kcal", 0) or 0.0)

    # If remaining calories are very low or negative, just give a light recommendation or nothing?
    # But usually users want to see something. We'll proceed.

    candidates = CatalogFood.query.all()
    if not candidates:
        return {"items": [], "meals": []}
    
    # Pre-filtering
    candidates = [item for item in candidates if _is_plausible_food(item)]

    # --- Profiling & Preferences (Keep existing logic) ---
    goal_type = (profile.goal_type or "balance").lower()
    metrics = _profile_metrics(profile)
    bmi = metrics["bmi"] or 22
    sex = (metrics["sex"] or "").lower()
    activity_level = (profile.activity_level or "moderate").lower()
    
    # We will use simple calorie targets for this iteration
    estimated_kcal = _estimate_calories(profile)
    
    # Weights for meal split
    meal_split = [0.3, 0.4, 0.3] # Default balance
    if sex == "male":
        meal_split = [0.26, 0.425, 0.315]
    elif sex == "female":
        meal_split = [0.32, 0.4, 0.28]
    
    if activity_level == "high":
        meal_split[1] += 0.05; meal_split[2] += 0.02; meal_split[0] -= 0.07;
    elif activity_level == "low":
        meal_split[0] += 0.05; meal_split[2] -= 0.05;
    
    # Normalize
    s = sum(meal_split)
    meal_split = [x/s for x in meal_split]

    MEAL_DEFINITIONS = [
        ("breakfast", "아침", meal_split[0]),
        ("lunch", "점심", meal_split[1]),
        ("dinner", "저녁", meal_split[2]),
    ]
    
    # --- Tracking Usage to avoid duplicates ---
    used_names = set()
    if exclude_names:
        for n in exclude_names:
            norm = _normalize_name(n)
            if norm: used_names.add(norm)
    
    flat_items = []
    meals_result = []

    def _get_valid_candidates(pool, current_meal_items):
        # Filter out used names and items too similar to what's in current meal
        valid = []
        current_names = {_normalize_name(x['name']) for x in current_meal_items}
        
        for food in pool:
            norm = _normalize_name(food.name)
            if not norm: continue
            if norm in used_names: continue
            if norm in current_names: continue
            valid.append(food)
        return valid

    for key, label, ratio in MEAL_DEFINITIONS:
        # 1. Determine Target for this meal
        # We base it on REMAINING calories distributed, but constrained?
        # If user has 2000 remaining, and it's breakfast time, maybe we shouldn't suggest 2000?
        # But 'recommend' usually implies "plan for the day". 
        # The existing logic seemed to slice 'remain' by ratio. Let's stick to that.
        
        target_kcal = max(remain_kcal * ratio, 0)
        # However, if target is too small (e.g. 50kcal), we might want minimums
        
        meal_items = []
        current_kcal = 0

        main_ratio = 0.7 if target_kcal > 500 else 0.9
        main_target = target_kcal * main_ratio
        
        valid_pool = _get_valid_candidates(candidates, meal_items)
        if not valid_pool: break

        # Heuristic: Score by abs(kcal - main_target)
        # Add some randomness to avoid always same result
        def score_main(f):
            k = _macro(f.kcal)
            diff = abs(k - main_target)
            return diff + rng.uniform(0, 30) # Random jitter
            
        main_dish = min(valid_pool, key=score_main)
        
        # Add Main
        serialized_main = serialize_food(main_dish)
        meal_items.append(serialized_main)
        used_names.add(_normalize_name(main_dish.name))
        current_kcal += _macro(main_dish.kcal)
        
        # Step B: Select Side Dishes (Fill the gap)
        # Allow up to 2 sides (total 3 items)
        max_items = 3
        
        while len(meal_items) < max_items:
            gap = target_kcal - current_kcal
            
            # We want to force finding items until max_items is reached
            # even if gap is small. We will just look for the best fitting (small) item.
            
            valid_pool = _get_valid_candidates(candidates, meal_items)
            if not valid_pool: break
            
            # Prefer different food_type from main if possible?
            main_type = serialized_main['food_type']
            
            def score_side(f):
                k = _macro(f.kcal)
                diff = abs(k - gap)
                
                # Variety bonus
                ftype = _food_type(f)
                type_penalty = 0 if ftype != main_type else 20
                
                return diff + type_penalty + rng.uniform(0, 20)
                
            side_dish = min(valid_pool, key=score_side)
            
            serialized_side = serialize_food(side_dish)
            meal_items.append(serialized_side)
            used_names.add(_normalize_name(side_dish.name))
            current_kcal += _macro(side_dish.kcal)
            
        # Compile Meal Stats
        meal_targets = {
            "kcal": target_kcal,
            "protein_g": dash["target"]["protein_g"] * ratio, # Rough estimate
            "fat_g": dash["target"]["fat_g"] * ratio,
            "carb_g": dash["target"]["carb_g"] * ratio,
        }
        
        meals_result.append({
            "key": key,
            "label": label,
            "ratio": ratio,
            "targets": meal_targets,
            "items": meal_items
        })
        flat_items.extend(meal_items)

    return {"meals": meals_result, "items": flat_items}




def _calc_ideal_duration(profile_obj):
    """Shared logic for calculating ideal workout duration."""
    # Base duration
    base = 30
    
    # Goal adjustment
    g_type = getattr(profile_obj, 'goal_type', 'balance') or 'balance'
    if g_type == "cut":
        base += 20 # Target ~50m
    elif g_type == "gain_muscle":
        base += 10 # Target ~40m
    
    # Activity adjustment
    act = (getattr(profile_obj, 'activity_level', 'moderate') or 'moderate').lower()
    if act == "high":
        base += 10
    elif act == "low":
        base -= 5
        
    return max(20, min(base, 90)) # Clamp between 20 and 90 minutes

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
    
    # Calculate recommended exercise minutes
    rec_minutes = _calc_ideal_duration(profile_stub)
    
    return {
        "goal_kcal": targets["kcal"],
        "protein_g": targets["protein_g"],
        "fat_g": targets["fat_g"],
        "carb_g": targets["carb_g"],
        "exercise_minutes": rec_minutes,
    }


def recommend_workouts(
    user_id: str, topn: int = 3, minutes: int = 20, exclude_names: list[str] | None = None
):
    profile = UserProfile.query.get(user_id)
    dash = dashboard(user_id)
    if not dash or not profile:
        return {"items": [], "requested_minutes": minutes, "assigned_minutes": 0, "recommended_minutes": 0}

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
    
    # Calculate IDEAL duration based on profile
    ideal_minutes = _calc_ideal_duration(profile)

    # Determine TARGET duration (Requested > Ideal)
    # If minutes is None/0, use ideal. Otherwise use requested.
    if minutes and minutes > 0:
        target_minutes = minutes
    else:
        target_minutes = ideal_minutes
    
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
        
        if remain_kcal_value < 0:
            target_burn = abs(remain_kcal_value)
            if est_burn < target_burn:
                burn_penalty = (target_burn - est_burn) * 1.5
            else:
                burn_penalty = 0
        else:
            if goal_type == "cut":
                burn_penalty = max(0, 300 - est_burn) * 0.5
            elif goal_type == "gain_muscle":
                burn_penalty = abs(est_burn - 250) * 0.5
            else:
                burn_penalty = 0

        time_gap = abs(est_minutes - remain_minutes)
        
        if workout.mets < met_low:
            intensity_penalty = (met_low - workout.mets) ** 2
        elif workout.mets > met_high:
            intensity_penalty = (workout.mets - met_high) ** 2
        else:
            intensity_penalty = 0
            
        return (
            burn_penalty
            + time_gap * 4 * intensity_bias(workout.category, workout.mets)
            + intensity_penalty * 8
        )
        
    remaining = target_minutes
    selected = []
    MIN_SLOT_MINUTES = 10

    def _remove_from_pools(workout):
        if workout in primary_pool:
            primary_pool.remove(workout)
        if workout in fallback_pool:
            fallback_pool.remove(workout)

    def _can_use(workout, allow_excluded=False):
        norm = _normalize_name(workout.name)
        if not norm: return False
        if norm in used_norms: return False
        if not allow_excluded and norm in excluded: return False
        return True

    def _get_pool(category: str | None, allow_excluded=False):
        sources = [primary_pool, fallback_pool]
        for source in sources:
            filtered = [w for w in source if (category is None or w.category == category) and _can_use(w, allow_excluded)]
            if filtered: return filtered
        return []

    while fallback_pool and remaining > 0 and len(selected) < topn:
        desired_category = category_sequence[len(selected) % len(category_sequence)]
        pool = _get_pool(desired_category, allow_excluded=False)
        if not pool: pool = _get_pool(None, allow_excluded=False)
        if not pool: pool = _get_pool(desired_category, allow_excluded=True)
        if not pool: pool = _get_pool(None, allow_excluded=True)
        if not pool: break

        slots_left = topn - len(selected)
        reserved = (slots_left - 1) * MIN_SLOT_MINUTES
        budget = remaining - reserved
        
        if not pool:
            break

        workout = max(pool, key=lambda w: score(w, budget, dash["remain"]["kcal"]))
        
        actual_min = min(workout.max_minutes or budget, budget)
        actual_min = max(actual_min, workout.min_minutes or 10)
        
        if len(selected) == topn - 1:
             actual_min = min(workout.max_minutes or remaining, remaining)

        actual_min = min(actual_min, remaining)
        
        selected.append(SimpleNamespace(
            id=workout.workout_id,
            name=workout.name,
            category=workout.category,
            mets=workout.mets,
            suggested_minutes=actual_min,
            per_min_kcal=workout.mets * weight * 0.0175,
            total_kcal=workout.mets * weight * 0.0175 * actual_min
        ))
        
        remaining -= actual_min
        _remove_from_pools(workout)
        used_norms.add(_normalize_name(workout.name))

    # Post-processing: If time remains, distribute it to items that can extend
    if remaining > 0 and selected:
        # Sort by those who can take more time (no max, or max > current)
        # Or just distribute to the ones with largest current duration (likely cardio)
        candidates_for_extension = []
        for item in selected:
            # Re-fetch original workout for limits (or store in item)
            # We didn't store max_minutes in item, so we rely on heuristic or need to look up.
            # Simplified: Just add to items with high METs (Cardio) or largest duration
            candidates_for_extension.append(item)
        
        # Simple round-robin distribution
        while remaining > 0 and candidates_for_extension:
            made_change = False
            for item in candidates_for_extension:
                if remaining <= 0: break
                # limit extension per item? Let's say we trust the user's total over the strict db limit for now
                add = min(remaining, 5) # Add 5 mins at a time
                item.suggested_minutes += add
                item.total_kcal = item.per_min_kcal * item.suggested_minutes
                remaining -= add
                made_change = True
            if not made_change: break # Should not happen if we force add

    # Cleanup metadata and serialize
    result_items = []
    for x in selected:
        d = vars(x)
        d.pop("min_minutes", None)
        d.pop("max_minutes", None)
        result_items.append(d)

    return {
        "items": result_items,
        "requested_minutes": target_minutes,
        "recommended_minutes": ideal_minutes,
        "assigned_minutes": sum(x.suggested_minutes for x in selected)
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
        
        net = eat - burn
        # Compliance: +/- 10% of target? Or just below target for cut?
        # Let's use a simple range: target +/- 15%
        lower = target * 0.85
        upper = target * 1.15
        
        status = "good"
        if net < lower:
            status = "low"
        elif net > upper:
            status = "high"
            
        days_list.append({
            "date": day_str,
            "eaten": round(eat, 1),
            "burned": round(burn, 1),
            "net": round(net, 1),
            "target": round(target, 1),
            "status": status
        })
        
        if status == "good":
            compliance.append(1)
        else:
            compliance.append(0)

    avg_compliance = sum(compliance) / len(compliance) if compliance else 0.0
    
    eat_values = [d["eaten"] for d in days_list]
    burn_values = [d["burned"] for d in days_list]
    
    avg_eat = sum(eat_values) / len(eat_values) if eat_values else 0.0
    avg_burn = sum(burn_values) / len(burn_values) if burn_values else 0.0
    max_eat = max(eat_values) if eat_values else 0.0
    min_eat = min(eat_values) if eat_values else 0.0
    
    return {
        "days": days_list,
        "summary": {
            "avg_compliance": round(avg_compliance * 100, 1),
            "avg_eat": round(avg_eat, 1),
            "avg_burn": round(avg_burn, 1),
            "max_eat": round(max_eat, 1),
            "min_eat": round(min_eat, 1),
            "compliance": round(avg_compliance * 100, 1),
            "target_daily": round(target, 1)
        }
    }
    return {
        "days": days_list,
        "summary": {
            "avg_compliance": round(avg_compliance * 100, 1),
            "avg_eat": round(avg_eat, 1),
            "avg_burn": round(avg_burn, 1),
            "max_eat": round(max_eat, 1),
            "min_eat": round(min_eat, 1),
            "compliance": round(avg_compliance * 100, 1),
            "target_daily": round(target, 1)
        }
    }


def get_ai_coach_message(user_id: str) -> dict:
    dash = dashboard(user_id)
    if not dash:
        return {"message": "데이터가 없습니다."}
    
    # Construct context
    target = dash["target"]["kcal"]
    eaten = dash["eaten"]["kcal"]
    burn = dash["burn"]
    remain = dash["remain"]["kcal"]
    
    context = (
        f"Target Calories: {target}, Eaten: {eaten}, Burned: {burn}, Remaining: {remain}. "
        f"Macros Eaten - Protein: {dash['eaten']['protein_g']}g, Fat: {dash['eaten']['fat_g']}g, Carb: {dash['eaten']['carb_g']}g."
    )
    
    from .ai import get_ai_service
    ai = get_ai_service()
    message = ai.generate_tip(context)
    
    return {"message": message}
