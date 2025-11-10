# NutriFit Data Sources

| 출처 | 요약 | 활용 방법 |
| --- | --- | --- |
| **식품의약품안전처 식품영양성분DB**<br>https://www.data.go.kr/data/15127578/openapi.do | 식품명, 식품분류, 영양성분(에너지, 탄수화물, 단백질, 지방 등), 출처, 제조사, 1회 섭취량 등을 제공하는 Open API | `.env`에 `MFDS_API_KEY`를 설정하고 `python fetch_food_api.py --pages 10 --per-page 100` 실행 → `catalog_food` 테이블에 최신 데이터 적재. 대량 적재 시 `--truncate`로 초기화 후 Sync 가능. |
| **식약처 통합 식품영양성분 CSV** (`data/식품의약품안전처_통합식품영양성분정보_20250630.csv`) | MFDS 포털에서 내려받은 전체 CSV. API 호출 없이도 15만+ 식품 영양 데이터를 제공 | `python load_food_catalog.py --path data/식품의약품안전처_통합식품영양성분정보_20250630.csv --truncate`로 전체 카탈로그 초기화 및 동기화. |

> KNHANES, Physical Activity Classification Table 등의 추가 레퍼런스는 모델 고도화 및 운동 추천 난이도 조정 시 참고.
