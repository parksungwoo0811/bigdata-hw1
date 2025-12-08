# 🥗 NutriFit (뉴트리핏)

> **"데이터로 설계하는 나만의 건강 라이프"**
> **Big Data & AI Powered Personal Health Coach**

## 📖 프로젝트 소개
**NutriFit**은 사용자의 신체 데이터와 행동 로그를 분석하여, 개인에게 최적화된 식단과 운동을 과학적으로 추천해주는 **지능형 헬스케어 플랫폼**입니다.
기존의 천편일률적인 다이어트 앱과 달리, **빅데이터 알고리즘**과 **생성형 AI(Google Gemini)**를 활용하여 정밀한 개인 맞춤형 솔루션을 제공합니다.

## 🚀 핵심 기능 (Key Features)

### 1. 📊 스마트 대시보드 (Smart Dashboard)
- **개인화 분석**: 사용자 프로필(키, 체중, 나이, 목표)을 기반으로 기초대사량(BMR)과 일일 권장 칼로리(TDEE)를 정밀 산출합니다.
- **실시간 모니터링**: '섭취 vs 소모' 칼로리 밸런스를 직관적인 그래프로 시각화하여 보여줍니다.

### 2. 🤖 AI 로거 (AI Natural Language Logger)
- **자연어 처리**: "오늘 점심에 김치찌개랑 밥 한 공기 먹었어"라고 말하면, AI가 자동으로 음식명과 영양 성분(JSON)을 분석해 기록합니다.
- **편의성 극대화**: 번거로운 검색과 수기 입력 과정을 획기적으로 단축했습니다.

### 3. 🥗 정밀 추천 시스템 (Precision Recommendation)
- **알고리즘 매칭**: 현재 부족한 영양소를 계산하여, 데이터베이스(Catalog) 내에서 최적의 식품 조합을 추천합니다.
- **동적 운동 제안**: 사용자의 BMI와 컨디션에 맞춰 적절한 강도(METs)의 운동을 제안합니다.

### 4. 📈 주간 리포트 & 인사이트
- **데이터 시각화**: 7일간의 기록을 집계하여 목표 달성률(Compliance Score)을 제공하고, 다음 주 행동 지침을 안내합니다.

## 🛠 기술 스택 (Tech Stack)
- **Backend**: Python 3.13, Flask
- **Database**: SQLite, SQLAlchemy ORM
- **AI Engine**: Google Gemini Pro API (GenAI)
- **Frontend**: HTML5, CSS3, Jinja2 Template
