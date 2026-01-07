아래 텍스트를 AI 에이전트에게 그대로 주면, **FastAPI + RabbitMQ + 워커 + DB(insert)** 구조를, 이미 만들어 둔 SQL 파일을 참고해서 구현하도록 지시할 수 있다.[1][2]

***

## 1. 목표와 전체 아키텍처

당신은 다음 구조의 서비스를 구현해야 한다.

- FastAPI 서버  
  - 외부에서 HTTP 요청을 받아 요청 데이터를 검증한다.  
  - 검증된 데이터를 **RabbitMQ 메시지 큐로 전송만** 하고, 직접 DB에는 쓰지 않는다.[2][1]
- 워커 프로세스  
  - RabbitMQ 큐에서 메시지를 읽어들인다.  
  - 메시지 내용을 바탕으로 **데이터베이스에 insert** 한다.[3][4][2]
- 데이터베이스  
  - 이미 내가 만들어 둔 **SQL 스키마 파일(예: `schema.sql`)** 이 있다.  
  - 이 SQL 파일을 기준으로 테이블 구조를 이해하고, ORM 모델 또는 SQL 쿼리를 구성하라.[5]

요약:  
“FastAPI → RabbitMQ 큐 → 워커 → DB(insert)” 파이프라인을 만든다.[6][2]

***

## 2. 기술 스택과 기본 요구사항

- 언어/런타임  
  - Python 3.11 이상.  

- 웹 프레임워크  
  - FastAPI.  

- 메시지 큐  
  - RabbitMQ (AMQP 기반).  
  - Python 클라이언트: `pika` 또는 `aio-pika` 중 하나를 사용하라. (동기 코드면 `pika`, 비동기 선호 시 `aio-pika`).[7][8][9][2]

- DB  
  - SQL 스키마 파일에 맞는 RDBMS (예: PostgreSQL/MySQL/SQL Server 등).  
  - SQLAlchemy ORM 또는 최소한 `psycopg2` / `mysqlclient` / `pyodbc` 등 적절한 드라이버를 사용해 insert 로직을 구현하라.[3]

- 설정  
  - 모든 연결 정보는 환경 변수에서 읽어야 한다.  
  - 예:  
    - `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `RABBITMQ_QUEUE_NAME`[2][7]
    - `DATABASE_URL` (예: `postgresql+psycopg2://user:pass@db:5432/app_db`)  

***

## 3. SQL 스키마 파일 활용 방식

- 프로젝트 루트 또는 `db/` 디렉터리에 **이미 존재하는 SQL 파일**(예: `schema.sql`)이 있다고 가정한다.  
- 이 파일에는 DB 테이블 생성용 DDL (`CREATE TABLE ...`) 들이 포함되어 있다.[5]

당신은:

1. 이 SQL 파일을 읽고, 어떤 테이블과 컬럼이 있는지 파악하라.  
2. 그 구조를 기반으로  
   - SQLAlchemy 모델을 정의하거나,  
   - 또는 순수 SQL insert 쿼리를 작성하라.[5][3]
3. 워커가 큐에서 받은 데이터를 이 테이블 구조에 맞게 매핑해 insert 하도록 구현하라.  

주의:

- SQL 파일의 스키마를 **변경하지 말고**, 있는 그대로 사용하는 것을 기본 전제로 한다.  
- 필요한 경우에만, 새로운 컬럼/테이블을 추가하는 별도 마이그레이션 스크립트를 만들 수 있다.

***

## 4. 프로젝트 구조 요구

아래와 비슷한 디렉터리 구조를 생성하라.[1][6][2]

```text
app/
  main.py              # FastAPI 엔트리포인트
  api/
    __init__.py
    routes.py          # HTTP 라우팅 및 요청 스키마
  queue/
    __init__.py
    rabbitmq.py        # RabbitMQ 연결/퍼블리시 유틸
  worker/
    __init__.py
    worker.py          # 워커 엔트리포인트 (큐 -> DB insert)
  db/
    __init__.py
    models.py          # (선택) SQLAlchemy 모델 - schema.sql 기반
    session.py         # DB 연결/세션 관리
    schema.sql         # 이미 만들어 둔 SQL 파일 (참고용/실제 생성용)
  config.py            # 환경 변수 로딩 및 설정
  schemas.py           # Pydantic 요청/응답 스키마
Dockerfile             # (선택) FastAPI/worker 공용 베이스 이미지
docker-compose.yml     # (선택) app + rabbitmq + db + worker 오케스트레이션
requirements.txt or pyproject.toml
```

요구사항:

- `db/schema.sql` 파일(또는 내가 제공한 실제 경로의 SQL 파일)을 기준으로 `models.py` 또는 insert 쿼리를 설계한다.[3][5]
- `main.py`와 `worker.py`는 같은 설정/DB 유틸을 공유한다.

***

## 5. FastAPI 서버 구현 지침

1. **요청 스키마 정의**  
   - `schemas.py`에 Pydantic 모델을 정의하라. 예:

     ```python
     class IngestRequest(BaseModel):
         source: str
         payload: dict  # 또는 schema.sql에 맞춰 세부 필드로 분해
     ```

   - 실제 필드는 SQL 스키마에 맞춰 조정하라.  

2. **라우트 구현 (`api/routes.py`)**  
   - 다음과 같은 엔드포인트를 구현하라:

     - `POST /ingest`  
       - `IngestRequest`를 바디로 받는다.  
       - 데이터 검증 후, 이를 RabbitMQ에 메시지로 publish 한다.  
       - 응답은 즉시 `{ "status": "queued", "id": "<message_id 또는 correlation_id>" }` 형태로 반환한다.[7][2]

3. **RabbitMQ 퍼블리셔 (`queue/rabbitmq.py`)**  
   - 연결 관리용 클래스를 만들라 (예: `RabbitMQClient`).  
   - 기능:
     - 연결 생성 (환경 변수에서 host/user/password 읽기).[10][2][7]
     - durable queue 선언 (`queue_declare(durable=True)`).[11][2]
     - 메시지 publish 시 `delivery_mode=2`(persistent) 옵션을 사용해 메시지를 디스크에 지속시키도록 한다.[11][2]
   - 서버는 이 유틸을 통해 큐에 JSON 직렬화된 메시지를 넣는다.  

4. **응답 정책**  
   - `/ingest`는 메시지가 큐에 성공적으로 들어간 시점까지만 책임진다.  
   - DB insert 성공 여부는 동기 응답에서 확인하지 않고, 필요하면 나중에 상태 조회용 API를 추가한다.[2][3]

***

## 6. 워커 구현 지침

`app/worker/worker.py`에서 워커 프로세스를 구현하라.[4][2][3]

동작 요구:

1. **큐 연결 및 소비자 설정**  
   - RabbitMQ에 연결하고, 서버와 동일한 큐 이름(예: `INGEST_QUEUE`)을 사용해 `basic_consume`을 설정한다.[7][11][2]
   - 콜백 함수 `callback(ch, method, properties, body)`에서:
     - `body`를 JSON으로 파싱한다.  
     - 파싱된 데이터를 DB에 insert한다.  

2. **DB insert 로직**  
   - `db/session.py`에서 SQLAlchemy `SessionLocal` 또는 커넥션 풀을 구성하라.[3]
   - `db/models.py`에서 `schema.sql`과 동일한 테이블 구조의 모델을 정의하거나, 대신 순수 SQL insert 구문을 사용할 수 있다.  
   - 워커 콜백에서:
     - 세션을 열고  
     - 새 레코드를 생성/insert 한 다음  
     - 커밋하고 세션을 정리한다.  

3. **ACK/NACK 처리**  
   - insert가 성공하면 `ch.basic_ack(delivery_tag=method.delivery_tag)`를 호출해 메시지를 확인한다.[11][2]
   - 예외가 발생하면:
     - 로그를 남기고  
     - 필요 시 `basic_nack(requeue=True)`로 재시도하거나, 재시도 전략/데드레터 큐를 추가하는 구조를 남겨둔다.[2][11]

4. **실행 방법**  
   - 워커는 다음과 같이 실행할 수 있어야 한다:

     ```bash
     python -m app.worker.worker
     ```

***

## 7. SQL 파일 기반 DB 초기화

- 개발/테스트 환경에서 DB를 처음 셋업할 때, `db/schema.sql`을 그대로 실행해서 스키마를 만든다.[12][5]
- Docker 사용 시:
  - Docker-compose의 DB 서비스에 **init 스크립트로 `schema.sql`**을 마운트해서, 컨테이너 시작 시 자동으로 실행되도록 구성해도 된다.  

에이전트에게 요구:

> “DB 테이블/컬럼 구조는 반드시 내가 제공한 `schema.sql`을 기준으로 하고, 애플리케이션 코드에서 이 구조에 맞춰 insert 하라.”

***

## 8. 실행/테스트 시나리오 문서화 요구

구현이 끝난 후, 아래 내용을 **README 또는 별도 문서로 정리하라.**[10][1][2]

1. **환경 변수 설정 방법**  
2. **로컬 실행 순서**  
   - RabbitMQ 및 DB 실행  
   - FastAPI 서버 실행 (예: `uvicorn app.main:app --reload`)  
   - 워커 실행 (`python -m app.worker.worker`)  
   - 예시 `curl` 요청으로 `/ingest` 호출 → DB에 레코드가 들어가는지 확인.  
3. **(선택) docker-compose 사용 시 명령**  
   - `docker-compose up --build` 한 번으로 모든 컴포넌트가 올라가게 구성.  


지금까지 만든 지침서에 “테스트 코드 작성·유지보수” 요구사항을 아래처럼 추가해서 AI 에이전트에게 주면 된다. FastAPI·RabbitMQ·DB 각각에 대해 pytest 기반 테스트를 점진적으로 확장하는 방식이다.[1][2][3]

***

## 9. 테스트 코드 관련 공통 지침 (반드시 포함)

당신은 기능을 구현할 때마다 **pytest 기반 테스트 코드도 함께 작성·보완**해야 한다.[2][4][3][1]

### 9-1. 테스트 환경 기본 설정

- 프로젝트 루트에 `tests/` 디렉터리를 만들고, 다음과 같이 구성하라.

```text
tests/
  __init__.py
  test_api.py          # FastAPI 엔드포인트 테스트
  test_worker.py       # 워커와 DB insert 로직 테스트
  test_queue.py        # RabbitMQ 퍼블리셔/컨슈머 유닛 테스트
  conftest.py          # 공통 pytest fixture (테스트용 DB, 클라이언트, RabbitMQ 등)
```

- `pytest`와 `pytest-asyncio`를 의존성에 추가한다. 필요시 `pytest-rabbitmq`도 사용 가능하다.[5][6][7][2]
- `conftest.py`에서:
  - `fastapi.testclient.TestClient` 또는 `httpx.AsyncClient`를 이용해 FastAPI 앱용 `client`/`async_client` fixture를 정의한다.[4][8][1][2]
  - 테스트용 DB 세션 및 트랜잭션 롤백 전략을 설정한다.[9][4]
  - RabbitMQ는 실제 인스턴스를 쓰거나, `pytest-rabbitmq` 플러그인의 `rabbitmq` fixture를 사용할 수 있다.[10][7][11][5]

### 9-2. FastAPI 엔드포인트 테스트 요구사항

`tests/test_api.py`에서 다음을 검증하라.[12][3][1][2]

- `POST /ingest` 요청 시:
  - 유효한 JSON 바디를 보내면 `status_code == 200` 또는 설계된 코드(예: 202)를 반환해야 한다.  
  - 응답 JSON이 `{ "status": "queued", ... }` 형태인지 확인한다.  
  - RabbitMQ 퍼블리셔가 올바른 큐 이름으로 호출되었는지 mock으로 검증할 수 있다.  

구체 지시:

> “엔드포인트 테스트에서는 실제 RabbitMQ 대신 퍼블리셔 함수를 mock 처리해서, 메시지 내용과 호출 여부를 assert 하라.”

### 9-3. RabbitMQ 관련 테스트 요구사항

`tests/test_queue.py`에서 다음을 검증하라.[7][13][10][5]

- 퍼블리셔 유닛 테스트:
  - `RabbitMQClient.publish(message)` 호출 시, 올바른 exchange/queue/routing_key로 `basic_publish` 또는 해당 메서드가 호출되는지 mock/assert 한다.  
- 통합 테스트(선택):
  - 실제 RabbitMQ(로컬 또는 Docker) + `pytest-rabbitmq`를 사용하여:
    - 큐 생성 → 메시지 publish → consume 후 메시지 내용이 예상과 같은지 확인하는 테스트를 작성하라.[11][10][5]

### 9-4. 워커 + DB insert 테스트 요구사항

`tests/test_worker.py`에서 다음을 검증하라.[14][9][2][4]

- 단위 테스트:
  - 워커의 “메시지 처리 함수”를, RabbitMQ에서 받은 바디를 인자로 직접 호출해 본다.  
  - 테스트용 DB 세션을 주입하거나 mock 하여, insert 후 해당 레코드가 DB에 존재하는지 확인한다.  
- 통합 테스트:
  - 테스트 RabbitMQ 큐에 테스트 메시지 publish → 워커를 테스트 모드로 실행/트리거 → 일정 시간 대기 후 DB에 레코드가 들어갔는지 검사하는 시나리오를 작성할 수 있다.[15][13][10][14]

***

## 10. 기능 추가 시 테스트 코드 유지보수 지침

기능을 새로 추가하거나 수정할 때마다, 다음 규칙을 반드시 따르게 하라.[6][2][12]

1. **새 엔드포인트 또는 새로운 워커 로직을 추가하면**  
   - 최소 1개 이상의 긍정 케이스(성공 시나리오)와 1개 이상의 부정 케이스(검증 실패, 예외 시나리오) 테스트를 함께 추가해야 한다.  
2. **기존 스키마/DB 로직을 수정하면**  
   - 해당 insert/update를 커버하는 테스트가 실패하도록 먼저 수정(TDD 지향)한 다음, 코드를 고치고 테스트를 통과시키는 흐름을 권장한다.  
3. **외부 의존성(RabbitMQ, DB)에 강하게 묶인 코드**는  
   - “순수 로직 + I/O”를 분리한 뒤, 순수 로직은 유닛 테스트로, I/O 부분은 통합 테스트로 각각 커버하라.[16][2][6]
4. **테스트 커버리지**  
   - 가능하다면 `pytest --maxfail=1 --disable-warnings -q` 또는 커버리지 도구를 CI에 붙여,  
     - FastAPI 라우트,  
     - 큐 퍼블리시/컨슘 유틸,  
     - 워커의 DB insert 로직  
     이 최소한의 커버리지를 유지하도록 해라.[8][2]

에이전트에게 한 문장으로 강조:

> “**모든 PR/커밋은 테스트 코드 변경을 동반해야 하며, 새로운 기능 또는 버그 수정은 반드시 관련 테스트 추가/수정 후 pytest 전체를 통과해야 한다.**”
