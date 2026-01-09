# Ingest Batch Plan

## 요구사항 요약
- 아래 필드는 요청 1회에 여러 개가 들어오는 구조로 확장 필요
  - metric_name, metric_unit, class_name, measure_item, measurable
  - x_index, y_index, x_0, x_1, y_0, y_1, value
- 그 외 필드는 요청 1회에 1번만 전달되어도 충분

## 설계 방향
1) 요청 스키마 변경
   - 상단 공통 필드(제품/사이트/노드/모듈/레시피/파일/lot/wf)를 분리
   - 측정 값은 배열(list)로 전달
   - Pydantic nested model 구조 활용 (Context7 참고)

2) 큐 메시지 구조 변경
   - RabbitMQ payload에 공통 메타 + measurements 배열 포함
   - 메시지 크기 고려: 측정값 수가 많을 경우 batch size 제한 또는 분할 정책 필요

3) 워커 처리 로직 변경
   - 공통 엔티티는 1회만 get-or-create
   - measurements 배열을 순회하며 measurement_items / measurement_raw_data를 다건 insert
   - 중복 키(uk_raw_file_item_xy) 처리 전략 명확화

4) 테스트 업데이트
   - /ingest에 measurements 배열 입력 테스트
   - 워커의 다건 insert 동작 및 중복 처리 테스트

## Pydantic 스키마 예시 (개념)
- IngestRequest
  - product_name, site_name, node_name, module_name
  - recipe_name, recipe_version, file_path, file_name
  - lot_name, wf_number
  - measurements: list[MeasurementPoint]

- MeasurementPoint
  - metric_name, metric_unit
  - class_name, measure_item
  - measurable
  - x_index, y_index, x_0, x_1, y_0, y_1, value

## 작업 단계
1) schemas.py: nested list 스키마 정의
2) routes.py: payload 검증 및 publish 구조 변경
3) worker.py: batch insert 로직으로 변경
4) tests: API/worker 테스트 리뉴얼
5) README: 변경된 요청 예시 반영
