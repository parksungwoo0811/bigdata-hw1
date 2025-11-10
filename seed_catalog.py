from nutrifit import create_app, db
from nutrifit.models import CatalogFood, CatalogWorkout

app = create_app()


FOOD_DATA = [
    {
        "name": "닭가슴살 150g",
        "kcal": 165,
        "protein_g": 31,
        "fat_g": 3.6,
        "carb_g": 0,
        "tags": "korean,high_protein",
    },
    {
        "name": "현미밥 210g",
        "kcal": 280,
        "protein_g": 6,
        "fat_g": 2,
        "carb_g": 60,
        "tags": "korean,vegan",
    },
    {
        "name": "샐러드(올리브X)",
        "kcal": 120,
        "protein_g": 4,
        "fat_g": 3,
        "carb_g": 20,
        "tags": "vegan,low_fat",
    },
    {
        "name": "두부 150g",
        "kcal": 120,
        "protein_g": 15,
        "fat_g": 7,
        "carb_g": 2,
        "tags": "vegan,halal",
    },
    {
        "name": "요거트 200g",
        "kcal": 130,
        "protein_g": 12,
        "fat_g": 2,
        "carb_g": 16,
        "tags": "dairy",
    },
]

WORKOUT_DATA = [
    # 기존 기본 운동
    {"name": "속도걷기", "mets": 3.8, "category": "cardio", "min_minutes": 10, "max_minutes": 40},
    {"name": "조깅", "mets": 7.0, "category": "cardio", "min_minutes": 10, "max_minutes": 30},
    {"name": "스쿼트루틴", "mets": 6.0, "category": "strength", "min_minutes": 10, "max_minutes": 25},
    {"name": "전신스트레칭", "mets": 2.5, "category": "stretch", "min_minutes": 10, "max_minutes": 20},
    {"name": "실내 자전거 HIIT", "mets": 8.5, "category": "cardio", "min_minutes": 15, "max_minutes": 45},
    {"name": "전신 컨디셔닝 서킷", "mets": 6.5, "category": "strength", "min_minutes": 15, "max_minutes": 35},
    {"name": "요가 & 필라테스", "mets": 3.0, "category": "stretch", "min_minutes": 20, "max_minutes": 50},
    {"name": "댄스 피트니스", "mets": 5.0, "category": "cardio", "min_minutes": 20, "max_minutes": 50},
    {"name": "런닝 인터벌", "mets": 9.0, "category": "cardio", "min_minutes": 10, "max_minutes": 40},
    {"name": "자유형 수영", "mets": 6.0, "category": "cardio", "min_minutes": 15, "max_minutes": 40},
    {"name": "걷기+계단 오르기", "mets": 4.2, "category": "cardio", "min_minutes": 15, "max_minutes": 45},
    {"name": "겨울 스포츠 (스키/보드)", "mets": 7.0, "category": "cardio", "min_minutes": 20, "max_minutes": 60},

    # 생활/가사 활동
    {"name": "휴대폰/컴퓨터 사용 (서기)", "mets": 1.8, "category": "lifestyle", "min_minutes": 15, "max_minutes": 60},
    {"name": "관광 · 여행", "mets": 3.5, "category": "lifestyle", "min_minutes": 30, "max_minutes": 120},
    {"name": "수면", "mets": 0.95, "category": "sedentary", "min_minutes": 60, "max_minutes": 480},
    {"name": "누워서 TV / 휴식", "mets": 1.1, "category": "sedentary", "min_minutes": 20, "max_minutes": 180},
    {"name": "영화보기 · 독서", "mets": 1.4, "category": "sedentary", "min_minutes": 20, "max_minutes": 120},
    {"name": "악기 연주 (저강도)", "mets": 2.2, "category": "lifestyle", "min_minutes": 20, "max_minutes": 90},
    {"name": "드럼/락 기타 연주", "mets": 3.4, "category": "lifestyle", "min_minutes": 15, "max_minutes": 60},
    {"name": "반신욕 · 식사", "mets": 1.4, "category": "lifestyle", "min_minutes": 20, "max_minutes": 60},
    {"name": "면도 · 샤워", "mets": 2.3, "category": "lifestyle", "min_minutes": 10, "max_minutes": 30},
    {"name": "정원 물주기", "mets": 1.5, "category": "lifestyle", "min_minutes": 15, "max_minutes": 60},
    {"name": "정원 심기", "mets": 2.0, "category": "lifestyle", "min_minutes": 20, "max_minutes": 60},
    {"name": "과일/채소 따기", "mets": 3.7, "category": "lifestyle", "min_minutes": 20, "max_minutes": 60},
    {"name": "기도 · 예배 참여", "mets": 1.3, "category": "lifestyle", "min_minutes": 15, "max_minutes": 90},
    {"name": "찬송 · 활동적 예배", "mets": 1.9, "category": "lifestyle", "min_minutes": 20, "max_minutes": 60},
    {"name": "집 수리(약한 강도)", "mets": 2.5, "category": "lifestyle", "min_minutes": 20, "max_minutes": 60},
    {"name": "페인팅/도배", "mets": 3.2, "category": "lifestyle", "min_minutes": 20, "max_minutes": 60},
    {"name": "집 수리(중간 강도)", "mets": 4.5, "category": "lifestyle", "min_minutes": 20, "max_minutes": 60},
    {"name": "집 수리(강한 강도)", "mets": 6.0, "category": "lifestyle", "min_minutes": 15, "max_minutes": 45},
    {"name": "생활 걷기(저강도)", "mets": 2.3, "category": "cardio", "min_minutes": 15, "max_minutes": 60},
    {"name": "생활 걷기(중강도)", "mets": 3.4, "category": "cardio", "min_minutes": 15, "max_minutes": 50},
    {"name": "빠른 걷기", "mets": 4.8, "category": "cardio", "min_minutes": 15, "max_minutes": 60},
    {"name": "언덕 걷기(물건 9kg)", "mets": 6.9, "category": "cardio", "min_minutes": 15, "max_minutes": 45},
    {"name": "계단 오르기(10-19kg)", "mets": 8.3, "category": "cardio", "min_minutes": 10, "max_minutes": 30},
    {"name": "계단 오르기(20kg 이상)", "mets": 8.9, "category": "cardio", "min_minutes": 10, "max_minutes": 30},
    {"name": "교통수단 타기", "mets": 1.3, "category": "sedentary", "min_minutes": 15, "max_minutes": 90},
    {"name": "운전하기", "mets": 2.4, "category": "lifestyle", "min_minutes": 15, "max_minutes": 120},
    {"name": "조깅/걷기 복합", "mets": 6.4, "category": "cardio", "min_minutes": 10, "max_minutes": 40},
    {"name": "달리기 8km/h", "mets": 8.0, "category": "cardio", "min_minutes": 10, "max_minutes": 40},
    {"name": "달리기 9km/h", "mets": 9.4, "category": "cardio", "min_minutes": 10, "max_minutes": 35},
    {"name": "달리기 11km/h", "mets": 11.0, "category": "cardio", "min_minutes": 10, "max_minutes": 30},
    {"name": "달리기 13km/h", "mets": 12.3, "category": "cardio", "min_minutes": 10, "max_minutes": 25},
    {"name": "달리기 16km/h", "mets": 14.8, "category": "cardio", "min_minutes": 5, "max_minutes": 20},
    {"name": "달리기 17.5km/h", "mets": 16.0, "category": "cardio", "min_minutes": 5, "max_minutes": 15},
    {"name": "고강도 자전거타기", "mets": 7.2, "category": "cardio", "min_minutes": 15, "max_minutes": 60},
    {"name": "배낚시 · 얼음낚시", "mets": 2.0, "category": "lifestyle", "min_minutes": 30, "max_minutes": 120},
    {"name": "일반 낚시", "mets": 3.5, "category": "lifestyle", "min_minutes": 30, "max_minutes": 120},
    {"name": "댄스 리허설", "mets": 5.0, "category": "cardio", "min_minutes": 20, "max_minutes": 60},
    {"name": "댄스 공연/에어로빅", "mets": 7.3, "category": "cardio", "min_minutes": 20, "max_minutes": 50},
    {"name": "스케이팅/스키", "mets": 7.0, "category": "cardio", "min_minutes": 20, "max_minutes": 60},
    {"name": "스케이팅 시합", "mets": 13.3, "category": "cardio", "min_minutes": 10, "max_minutes": 30},
    {"name": "보트 승객", "mets": 1.3, "category": "sedentary", "min_minutes": 15, "max_minutes": 60},
    {"name": "수중 걷기(느리게)", "mets": 2.4, "category": "cardio", "min_minutes": 15, "max_minutes": 45},
    {"name": "서핑 · 윈드서핑", "mets": 3.3, "category": "cardio", "min_minutes": 20, "max_minutes": 60},
    {"name": "수영 배영/스노클", "mets": 5.0, "category": "cardio", "min_minutes": 20, "max_minutes": 60},
    {"name": "수영 (일반)", "mets": 6.8, "category": "cardio", "min_minutes": 20, "max_minutes": 60},
    {"name": "수영 접영", "mets": 13.8, "category": "cardio", "min_minutes": 10, "max_minutes": 30},
    {"name": "당구 · 캐치볼", "mets": 2.5, "category": "lifestyle", "min_minutes": 20, "max_minutes": 90},
    {"name": "골프(전동차)", "mets": 3.4, "category": "lifestyle", "min_minutes": 30, "max_minutes": 120},
    {"name": "골프(클럽 휴대)", "mets": 4.4, "category": "cardio", "min_minutes": 30, "max_minutes": 120},
    {"name": "배구 연습/체조", "mets": 3.4, "category": "cardio", "min_minutes": 20, "max_minutes": 60},
    {"name": "코칭/탁구/테니스 복식", "mets": 4.4, "category": "cardio", "min_minutes": 20, "max_minutes": 60},
    {"name": "배드민턴 · 승마", "mets": 5.3, "category": "cardio", "min_minutes": 20, "max_minutes": 60},
    {"name": "농구(일반) / 축구", "mets": 6.5, "category": "cardio", "min_minutes": 15, "max_minutes": 60},
    {"name": "농구 시합 / 스쿼시", "mets": 7.8, "category": "cardio", "min_minutes": 10, "max_minutes": 45},
    {"name": "무술 · 축구 시합", "mets": 9.9, "category": "cardio", "min_minutes": 10, "max_minutes": 45},
    {"name": "복싱/줄넘기 빠르게", "mets": 12.4, "category": "cardio", "min_minutes": 5, "max_minutes": 30},
    {"name": "요가(하타)", "mets": 2.5, "category": "stretch", "min_minutes": 20, "max_minutes": 60},
    {"name": "근력운동/필라테스", "mets": 3.4, "category": "strength", "min_minutes": 20, "max_minutes": 60},
    {"name": "헬스장 전신운동", "mets": 5.3, "category": "strength", "min_minutes": 20, "max_minutes": 60},
    {"name": "컨디셔닝 운동", "mets": 7.5, "category": "strength", "min_minutes": 15, "max_minutes": 45},
    {"name": "줄넘기 고강도", "mets": 12.3, "category": "cardio", "min_minutes": 5, "max_minutes": 30},
]



def _sync_catalog(model, dataset, unique_field="name"):
    """Upsert catalog rows by a unique field so rerunning the seed remains idempotent."""
    existing = {
        getattr(row, unique_field): row for row in model.query.all() if getattr(row, unique_field)
    }
    for entry in dataset:
        key = entry.get(unique_field)
        if not key:
            continue
        obj = existing.get(key)
        if obj:
            for field, value in entry.items():
                setattr(obj, field, value)
        else:
            db.session.add(model(**entry))


def seed():
    _sync_catalog(CatalogFood, FOOD_DATA)
    _sync_catalog(CatalogWorkout, WORKOUT_DATA)
    db.session.commit()
    print("Seed data inserted.")


if __name__ == "__main__":
    with app.app_context():
        seed()
