-- Add latest-only and history tables for raw data retention/performance.
-- Keeps measurement_raw_data as legacy until cutover is validated.

CREATE TABLE IF NOT EXISTS measurement_raw_data_current (
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

CREATE TABLE IF NOT EXISTS measurement_raw_data_history (
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

CREATE EVENT IF NOT EXISTS purge_raw_data_history
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP + INTERVAL 1 HOUR
DO
  DELETE FROM measurement_raw_data_history
  WHERE ingested_at < NOW() - INTERVAL 1 MONTH;

-- Optional backfill for current table (latest-only).
INSERT INTO measurement_raw_data_current (
  file_id, item_id, x_index, y_index, measurable,
  x_0, x_1, y_0, y_1, value
)
SELECT
  file_id, item_id, x_index, y_index, measurable,
  x_0, x_1, y_0, y_1, value
FROM measurement_raw_data
ON DUPLICATE KEY UPDATE
  measurable = VALUES(measurable),
  x_0 = VALUES(x_0),
  x_1 = VALUES(x_1),
  y_0 = VALUES(y_0),
  y_1 = VALUES(y_1),
  value = VALUES(value),
  updated_at = CURRENT_TIMESTAMP(6);

-- Optional backfill for history table.
INSERT INTO measurement_raw_data_history (
  file_id, item_id, x_index, y_index, measurable,
  x_0, x_1, y_0, y_1, value
)
SELECT
  file_id, item_id, x_index, y_index, measurable,
  x_0, x_1, y_0, y_1, value
FROM measurement_raw_data;
