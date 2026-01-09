# Measurement Save Server Worker

## 프로젝트 구조

```
.
├─ app/
│  ├─ main.py                # FastAPI 앱 엔트리포인트
│  ├─ config.py              # 환경 변수 로딩
│  ├─ schemas.py             # 요청/응답 스키마(Pydantic)
│  ├─ api/
│  │  └─ routes.py            # /ingest 라우팅
│  ├─ queue/
│  │  └─ rabbitmq.py          # RabbitMQ 연결/퍼블리시
│  ├─ worker/
│  │  └─ worker.py            # 워커 엔트리포인트 (큐 소비 -> DB insert)
│  └─ db/
│     ├─ models.py            # SQLAlchemy 모델
│     ├─ session.py           # DB 세션/엔진
│     └─ schema.sql           # DB 스키마 (create_db.sql 기반)
├─ tests/
│  ├─ conftest.py             # 테스트 공통 fixture
│  ├─ test_api.py             # API 테스트
│  ├─ test_queue.py           # RabbitMQ 퍼블리셔 테스트
│  └─ test_worker.py          # 워커/DB insert 테스트
├─ create_db.sql              # 원본 스키마
└─ README.md
```

## 기능별 설명 (한글)

- `app/main.py`
  - FastAPI 앱 생성 및 라우터 등록
- `app/config.py`
  - RabbitMQ/DB 연결 정보를 환경 변수로 읽어 Settings 구성
- `app/schemas.py`
  - `/ingest` 입력 데이터 검증용 Pydantic 모델 정의
- `app/api/routes.py`
  - `POST /ingest` 구현
  - 요청 검증 후 RabbitMQ에 메시지 publish, 즉시 `queued` 응답
- `app/queue/rabbitmq.py`
  - RabbitMQ 연결 관리 및 메시지 퍼블리시
  - durable queue 선언, persistent 메시지 설정
- `app/worker/worker.py`
  - 큐에서 메시지 소비
  - 메시지 내용을 DB 스키마에 맞게 insert
  - 성공 시 ACK, 실패 시 NACK(requeue)
- `app/db/models.py`
  - `schema.sql` 기반 SQLAlchemy 모델
- `app/db/session.py`
  - SQLAlchemy Engine/Session 생성
- `tests/*`
  - API/Queue/Worker에 대한 pytest 테스트

## FastAPI → RabbitMQ → Worker → DB 동작 구조

1) FastAPI (`/ingest`)
   - 클라이언트 요청을 받아 `schemas.py`로 데이터 검증
   - 검증된 payload를 RabbitMQ에 publish
   - DB에는 직접 쓰지 않음

2) RabbitMQ
   - durable queue에 메시지를 저장 (persistent)
   - 워커가 메시지를 가져갈 때까지 보관

3) Worker
   - 큐에서 메시지 consume
   - payload를 파싱하고 필요한 마스터/조합 테이블을 get-or-create
   - `measurement_files` 및 `measurement_raw_data`에 insert
   - 성공 시 ACK, 실패 시 NACK(requeue)

4) DB
   - `app/db/schema.sql`에 정의된 테이블 구조를 그대로 사용
   - 중복 키는 유니크 제약으로 방지

## 헬스체크/상태 확인

- `GET /health`
  - API 프로세스가 살아있는지 확인 (liveness)
- `GET /ready`
  - DB와 RabbitMQ 연결 가능 여부 확인 (readiness)
- `GET /metrics`
  - Prometheus 수집용 메트릭 노출

## 로그/메트릭 관리 방식

- 로그
  - JSON 형태로 stdout에 출력
  - 운영 환경에서는 로그 수집기(예: ELK, Cloud Logging)로 전송
- 메트릭
  - `prometheus_client`로 HTTP 요청 수/지연시간 수집
  - Prometheus에서 `/metrics`를 스크랩하고 Grafana로 시각화/알람

## Environment Variables

- `RABBITMQ_HOST` (default: `localhost`)
- `RABBITMQ_PORT` (default: `5672`)
- `RABBITMQ_USER` (default: `guest`)
- `RABBITMQ_PASSWORD` (default: `guest`)
- `RABBITMQ_QUEUE_NAME` (default: `measurement_ingest`)
- `DATABASE_URL` (default: `mysql+pymysql://user:password@localhost:3306/measure_system_3`)

환경 변수 예시는 `.env.example` 참고.

`.env` 파일을 만들고 `.env.example`을 복사해서 값만 수정하면 됩니다.

## 설치해야 하는 것

- Python 3.11+
- RabbitMQ (서버)
- MySQL (서버)
- Python 패키지 (가상환경 권장)

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
```

### Windows 환경 주의사항

- 가상환경 활성화:
  - `.\.venv\Scripts\activate`
- MySQL 클라이언트에서 스키마 적용 시 경로 구분자 주의
  - PowerShell 기준: `Get-Content app\db\schema.sql | mysql -u <user> -p`
- RabbitMQ는 Windows 서비스로 설치하거나 Docker 사용 권장

### Linux 환경 주의사항

- 서비스 설치/실행을 systemd로 관리하는 경우가 일반적
  - 예: `sudo systemctl start rabbitmq-server`, `sudo systemctl start mysql`
- 스키마 적용:
  - `mysql -u <user> -p < app/db/schema.sql`

## Local Run

1) Start RabbitMQ and MySQL
2) Initialize DB schema

```bash
mysql -u <user> -p < app/db/schema.sql
```

3) Start the API server

```bash
uvicorn app.main:app --reload
```

4) Start the worker

```bash
python -m app.worker.worker
```

5) Send an ingest request

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "P1",
    "site_name": "HC",
    "node_name": "2NM",
    "module_name": "PC",
    "recipe_name": "RCP",
    "recipe_version": "1.0",
    "file_path": "/data/measurements/measure1.csv",
    "file_name": "measure1.csv",
    "lot_name": "LOT001",
    "wf_number": 12,
    "measurements": [
      {
        "metric_name": "THK",
        "metric_unit": "nm",
        "class_name": "CLASS_A",
        "measure_item": "ITEM_1",
        "measurable": true,
        "x_index": 0,
        "y_index": 0,
        "x_0": 0.1,
        "y_0": 0.2,
        "x_1": 0.3,
        "y_1": 0.4,
        "value": 1.23
      },
      {
        "metric_name": "THK",
        "metric_unit": "nm",
        "class_name": "CLASS_A",
        "measure_item": "ITEM_1",
        "measurable": true,
        "x_index": 1,
        "y_index": 0,
        "x_0": 0.2,
        "y_0": 0.3,
        "x_1": 0.4,
        "y_1": 0.5,
        "value": 2.34
      }
    ]
  }'
```

## Tests

```bash
pytest -q
```

## Python 클라이언트 템플릿 (DataFrame / NumPy)

```python
import requests


def build_payload(common: dict, measurements: list[dict]) -> dict:
    payload = dict(common)
    payload["measurements"] = measurements
    return payload


def ingest_from_dataframe(api_url: str, common: dict, df):
    """
    df columns expected:
      metric_name, metric_unit, class_name, measure_item, measurable,
      x_index, y_index, x_0, y_0, x_1, y_1, value
    """
    measurements = []
    for row in df.to_dict(orient="records"):
        measurements.append(
            {
                "metric_name": row["metric_name"],
                "metric_unit": row.get("metric_unit"),
                "class_name": row["class_name"],
                "measure_item": row["measure_item"],
                "measurable": bool(row.get("measurable", True)),
                "x_index": int(row["x_index"]),
                "y_index": int(row["y_index"]),
                "x_0": float(row["x_0"]),
                "y_0": float(row["y_0"]),
                "x_1": float(row["x_1"]),
                "y_1": float(row["y_1"]),
                "value": float(row["value"]),
            }
        )

    payload = build_payload(common, measurements)
    response = requests.post(f"{api_url}/ingest", json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def ingest_from_numpy(api_url: str, common: dict, arr):
    """
    arr shape expected: (N, 12)
    columns order:
      metric_name, metric_unit, class_name, measure_item, measurable,
      x_index, y_index, x_0, y_0, x_1, y_1, value
    """
    measurements = []
    for row in arr:
        measurements.append(
            {
                "metric_name": row[0],
                "metric_unit": row[1],
                "class_name": row[2],
                "measure_item": row[3],
                "measurable": bool(row[4]),
                "x_index": int(row[5]),
                "y_index": int(row[6]),
                "x_0": float(row[7]),
                "y_0": float(row[8]),
                "x_1": float(row[9]),
                "y_1": float(row[10]),
                "value": float(row[11]),
            }
        )

    payload = build_payload(common, measurements)
    response = requests.post(f"{api_url}/ingest", json=payload, timeout=10)
    response.raise_for_status()
    return response.json()
```

### 사용 예시 (DataFrame)

```python
import pandas as pd

common = {
    "product_name": "P1",
    "site_name": "HC",
    "node_name": "2NM",
    "module_name": "PC",
    "recipe_name": "RCP",
    "recipe_version": "1.0",
    "file_path": "/data/measurements/measure1.csv",
    "file_name": "measure1.csv",
    "lot_name": "LOT001",
    "wf_number": 12,
}

df = pd.DataFrame(
    [
        {
            "metric_name": "THK",
            "metric_unit": "nm",
            "class_name": "CLASS_A",
            "measure_item": "ITEM_1",
            "measurable": True,
            "x_index": 0,
            "y_index": 0,
            "x_0": 0.1,
            "y_0": 0.2,
            "x_1": 0.3,
            "y_1": 0.4,
            "value": 1.23,
        },
        {
            "metric_name": "THK",
            "metric_unit": "nm",
            "class_name": "CLASS_A",
            "measure_item": "ITEM_1",
            "measurable": True,
            "x_index": 1,
            "y_index": 0,
            "x_0": 0.2,
            "y_0": 0.3,
            "x_1": 0.4,
            "y_1": 0.5,
            "value": 2.34,
        },
    ]
)

resp = ingest_from_dataframe("http://localhost:8000", common, df)
print(resp)
```

### 사용 예시 (NumPy)

```python
import numpy as np

common = {
    "product_name": "P1",
    "site_name": "HC",
    "node_name": "2NM",
    "module_name": "PC",
    "recipe_name": "RCP",
    "recipe_version": "1.0",
    "file_path": "/data/measurements/measure1.csv",
    "file_name": "measure1.csv",
    "lot_name": "LOT001",
    "wf_number": 12,
}

# columns:
# metric_name, metric_unit, class_name, measure_item, measurable,
# x_index, y_index, x_0, y_0, x_1, y_1, value
arr = np.array(
    [
        ["THK", "nm", "CLASS_A", "ITEM_1", True, 0, 0, 0.1, 0.2, 0.3, 0.4, 1.23],
        ["THK", "nm", "CLASS_A", "ITEM_1", True, 1, 0, 0.2, 0.3, 0.4, 0.5, 2.34],
    ]
)

resp = ingest_from_numpy(
    "http://localhost:8000",
    common,
    arr,
)
print(resp)
```
