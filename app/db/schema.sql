-- =========================================
-- 공통 설정
-- =========================================
-- UTF-8 full(emoji 포함) 지원. 문자열 인덱스 길이에 영향(utf8mb4는 문자당 최대 4 bytes).
SET NAMES utf8mb4;

-- 서버 세션 시간대. TIMESTAMP/DATETIME 처리 정책과 함께 운용해야 함.
SET time_zone = '+09:00';

-- 운영 DB 생성/선택
CREATE DATABASE IF NOT EXISTS measure_system
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE measure_system;

-- =========================================================
-- 1) Dimension / Master tables
--    (코드/마스터 성격: name 기반 lookup, is_active로 soft-disable)
-- =========================================================

-- [lot_wf]
-- 역할: LOT + WaferNumber 조합을 정규화해서 file에서 lot_wf_id로 참조.
-- 장점: 문자열 lot_name 중복 저장 감소 + lot/wf 기준 조회/집계 쉬움.
CREATE TABLE lot_wf (
  id        INT AUTO_INCREMENT PRIMARY KEY,         -- PK: surrogate key (INT면 충분한 규모라고 판단)
  lot_name  VARCHAR(128) NOT NULL,                  -- 예: RNTAS.5
  wf_number INT NOT NULL,                           -- wafer number (정수로 관리)

  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- 생성 시각(감사/추적용)

  -- 제약: 동일 LOT에서 동일 wafer가 중복 등록되지 않도록 보장
  UNIQUE KEY uk_lot_wf (lot_name, wf_number),

  -- 인덱스: lot만으로 조회하거나, wf_number 단독 필터링이 있을 때를 대비
  KEY idx_lot_name (lot_name),
  KEY idx_wf_number (wf_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- [nodes]
-- 역할: 기준정보 Node 
-- is_active: 삭제 대신 비활성화(soft disable)로 운영 안정성 확보(FK 연쇄삭제 방지).
CREATE TABLE spas_nodes (
  id   INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(128) NOT NULL,                       -- 예: 2NM, 5NM, 1.4NM
  is_active TINYINT(1) NOT NULL DEFAULT 1,          -- 1=활성, 0=비활성(신규 사용 제한)
  UNIQUE KEY uk_nodes_name (name)                   -- 동일 node name 중복 방지(자연키)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- [modules]
-- 역할: 기준정보 module.
CREATE TABLE spas_modules (
  id   INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(128) NOT NULL,                       -- 예: PC, RMG, MOL
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  UNIQUE KEY uk_modules_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- [spas_sites]
-- 역할: 기준정보 SPAS Site .
CREATE TABLE spas_sites (
  id   INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(128) NOT NULL,                       -- 예: HC, HD, ESPIN35
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  UNIQUE KEY uk_sites_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- [measurement_recipe]
-- 역할: recipe의 (name, version) 조합 마스터.
-- 주의: recipe는 “처리/측정 규칙 세트”로, 파일 데이터와 느슨하게 연결됨(필요 시 NULL 허용).
CREATE TABLE measurement_recipe (
  id      INT AUTO_INCREMENT PRIMARY KEY,
  name    VARCHAR(128) NOT NULL,                    -- recipe logical name
  version VARCHAR(64)  NOT NULL,                    -- 버전은 보통 문자열(v1.2.3, 2026.01.05 등)
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  -- 제약: 같은 recipe name에 같은 version 중복 등록 방지
  UNIQUE KEY uk_recipe_name_version (name, version),
  -- 조회 최적화: name으로 찾거나, version만으로 필터링하는 경우 대비
  KEY idx_recipe_name (name),
  KEY idx_recipe_version (version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- (권장) UNKNOWN recipe seed
INSERT INTO measurement_recipe (name, version)
VALUES ('UNKNOWN', '0')
ON DUPLICATE KEY UPDATE name=name;

-- [product_names]
-- 역할: product의 short name 마스터(코드 테이블).
-- 비활성화(is_active)로 신규 유입 차단 가능.
CREATE TABLE product_names (
  id        INT AUTO_INCREMENT PRIMARY KEY,         -- product_id로 사용(파일/기준정보에서 참조)
  name      VARCHAR(128) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  UNIQUE KEY uk_product_names_name (name)           -- product name 중복 방지
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- =========================================================
-- 2) 기준정보(조합) 테이블: spas_references
-- =========================================================
-- 역할:
--   product/site/node/module 조합을 “하나의 기준정보 id”로 캡슐화.
--   measurement_files에 여러 FK를 직접 두지 않고 reference_id 하나로 단순화.
-- 이점:
--   (1) measurement_files row 폭 감소(정규화)
--   (2) 동일 조합 재사용으로 중복 감소
--   (3) 조합 기반 집계/권한/설정 확장에 유리
CREATE TABLE spas_references (
  id         BIGINT AUTO_INCREMENT PRIMARY KEY,     -- 조합 테이블은 누적될 수 있어 BIGINT로 넉넉히

  product_id INT NOT NULL,
  site_id    INT NOT NULL,
  node_id    INT NOT NULL,
  module_id  INT NOT NULL,

  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_ref_product
    FOREIGN KEY (product_id) REFERENCES product_names(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,

  CONSTRAINT fk_ref_site
    FOREIGN KEY (site_id) REFERENCES spas_sites(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,

  CONSTRAINT fk_ref_node
    FOREIGN KEY (node_id) REFERENCES spas_nodes(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,

  CONSTRAINT fk_ref_module
    FOREIGN KEY (module_id) REFERENCES spas_modules(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,

  UNIQUE KEY uk_ref_combo (product_id, site_id, node_id, module_id),

  KEY idx_ref_product (product_id),
  KEY idx_ref_site (site_id),
  KEY idx_ref_node (node_id),
  KEY idx_ref_module (module_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- =========================================================
-- 3) Fact table: measurement_files
-- =========================================================
CREATE TABLE measurement_files (
  id           BIGINT AUTO_INCREMENT PRIMARY KEY,

  file_path    VARCHAR(2048) NOT NULL,
  file_name    VARCHAR(255) NOT NULL,

  reference_id BIGINT NOT NULL,
  lot_wf_id    INT NULL,

  recipe_id    INT NOT NULL,

  created_at   DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at   DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

  CONSTRAINT fk_files_reference
    FOREIGN KEY (reference_id) REFERENCES spas_references(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,

  CONSTRAINT fk_files_lot_wf
    FOREIGN KEY (lot_wf_id) REFERENCES lot_wf(id)
    ON DELETE SET NULL ON UPDATE CASCADE,

  CONSTRAINT fk_files_recipe
    FOREIGN KEY (recipe_id) REFERENCES measurement_recipe(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,

  UNIQUE KEY uk_files_path_recipe (file_path(512), recipe_id),

  KEY idx_files_created_at (created_at),
  KEY idx_files_reference (reference_id),
  KEY idx_files_lot_wf (lot_wf_id),
  KEY idx_files_recipe (recipe_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- =========================================================
-- 4) Measurement definitions: metric_types, measurement_items
-- =========================================================

CREATE TABLE metric_types (
  id        INT AUTO_INCREMENT PRIMARY KEY,
  name      VARCHAR(64) NOT NULL,
  unit      VARCHAR(32) NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  UNIQUE KEY uk_metric_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE measurement_items (
  id               BIGINT AUTO_INCREMENT PRIMARY KEY,
  class_name       VARCHAR(64) NOT NULL,
  measure_item     VARCHAR(64) NOT NULL,
  metric_type_id   INT NOT NULL,
  is_active        TINYINT(1) NOT NULL DEFAULT 1,

  CONSTRAINT fk_items_metric_type
    FOREIGN KEY (metric_type_id) REFERENCES metric_types(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,

  UNIQUE KEY uk_item_class_key (class_name, measure_item, metric_type_id),
  KEY idx_items_metric_type (metric_type_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- =========================================================
-- 5) Latest/History tables: measurement_raw_data_current, measurement_raw_data_history
-- =========================================================
CREATE TABLE measurement_raw_data_current (
  file_id    BIGINT NOT NULL,
  item_id    BIGINT NOT NULL,
  x_index    INT NOT NULL,
  y_index    INT NOT NULL,

  measurable TINYINT(1) NOT NULL DEFAULT 1,

  x_0        DOUBLE NOT NULL,
  x_1        DOUBLE NOT NULL,
  y_0        DOUBLE NOT NULL,
  y_1        DOUBLE NOT NULL,

  value      DOUBLE NOT NULL,

  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

  PRIMARY KEY (file_id, item_id, x_index, y_index),

  CONSTRAINT fk_current_file
    FOREIGN KEY (file_id) REFERENCES measurement_files(id)
    ON DELETE CASCADE ON UPDATE CASCADE,

  CONSTRAINT fk_current_item
    FOREIGN KEY (item_id) REFERENCES measurement_items(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,

  KEY idx_current_file (file_id),
  KEY idx_current_item (item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE measurement_raw_data_history (
  id         BIGINT AUTO_INCREMENT PRIMARY KEY,
  file_id    BIGINT NOT NULL,
  item_id    BIGINT NOT NULL,

  measurable TINYINT(1) NOT NULL DEFAULT 1,

  x_index    INT NOT NULL,
  y_index    INT NOT NULL,

  x_0        DOUBLE NOT NULL,
  x_1        DOUBLE NOT NULL,
  y_0        DOUBLE NOT NULL,
  y_1        DOUBLE NOT NULL,

  value      DOUBLE NOT NULL,

  ingested_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

  CONSTRAINT fk_history_file
    FOREIGN KEY (file_id) REFERENCES measurement_files(id)
    ON DELETE CASCADE ON UPDATE CASCADE,

  CONSTRAINT fk_history_item
    FOREIGN KEY (item_id) REFERENCES measurement_items(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,

  KEY idx_history_ingested_at (ingested_at),
  KEY idx_history_file_ingested (file_id, ingested_at),
  KEY idx_history_item (item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================
-- 7) Purge event: keep history for 1 month
-- =========================================================
CREATE EVENT IF NOT EXISTS purge_raw_data_history
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP + INTERVAL 1 HOUR
DO
  DELETE FROM measurement_raw_data_history
  WHERE ingested_at < NOW() - INTERVAL 1 MONTH;
