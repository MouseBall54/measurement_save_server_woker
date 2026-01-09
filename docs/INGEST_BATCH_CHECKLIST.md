# Ingest Batch Checklist

- [x] IngestRequest를 공통 필드 + measurements 배열 구조로 변경
- [x] MeasurementPoint Pydantic 모델 추가
- [x] RabbitMQ publish payload 구조 수정
- [x] worker: 공통 엔티티 1회 처리 + measurements 반복 insert
- [x] 중복 키 처리 전략 반영 (중복 skip 또는 update)
- [x] tests/test_api.py: measurements 배열 입력 테스트 추가
- [x] tests/test_worker.py: 다건 insert 및 중복 처리 테스트 추가
- [x] README: 요청 예시 및 설명 업데이트
