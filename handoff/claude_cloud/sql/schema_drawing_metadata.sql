-- Cloud Claude Code 検証用: drawing_metadata 関連テーブルの参照スキーマ

-- 通常は Django migrate 後に seed_drawing_metadata_minimal.sql を投入してください。

CREATE TABLE "drawing_metadata_drawingmetadataauditlog" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "action_type" varchar(32) NOT NULL, "reason" text NOT NULL, "before_json" text NOT NULL CHECK ((JSON_VALID("before_json") OR "before_json" IS NULL)), "after_json" text NOT NULL CHECK ((JSON_VALID("after_json") OR "after_json" IS NULL)), "executed_by" varchar(255) NOT NULL, "executed_at" datetime NOT NULL, "drawing_id" char(32) NOT NULL REFERENCES "drawing_metadata_registereddrawing" ("id") DEFERRABLE INITIALLY DEFERRED, "extraction_mode" varchar(8) NOT NULL);

CREATE TABLE "drawing_metadata_drawingmetadataextractionjob" ("id" char(32) NOT NULL PRIMARY KEY, "status" varchar(16) NOT NULL, "started_at" datetime NULL, "finished_at" datetime NULL, "elapsed_ms" integer unsigned NULL CHECK ("elapsed_ms" >= 0), "error_message" text NOT NULL, "warnings_json" text NOT NULL CHECK ((JSON_VALID("warnings_json") OR "warnings_json" IS NULL)), "extractor_name" varchar(128) NOT NULL, "extractor_version" varchar(64) NOT NULL, "schema_version" varchar(32) NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "drawing_id" char(32) NOT NULL REFERENCES "drawing_metadata_registereddrawing" ("id") DEFERRABLE INITIALLY DEFERRED, "extraction_mode" varchar(8) NOT NULL, "lease_expires_at" datetime NULL, "retry_count" integer unsigned NOT NULL CHECK ("retry_count" >= 0), "worker_name" varchar(255) NOT NULL, "diagnostics_json" text NOT NULL CHECK ((JSON_VALID("diagnostics_json") OR "diagnostics_json" IS NULL)), "extraction_options_json" text NOT NULL CHECK ((JSON_VALID("extraction_options_json") OR "extraction_options_json" IS NULL)), "extraction_profile" varchar(64) NOT NULL);

CREATE TABLE "drawing_metadata_drawingmetadatasnapshot" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "raw_extract_json" text NOT NULL CHECK ((JSON_VALID("raw_extract_json") OR "raw_extract_json" IS NULL)), "canonical_attributes_json" text NOT NULL CHECK ((JSON_VALID("canonical_attributes_json") OR "canonical_attributes_json" IS NULL)), "derived_tags_json" text NOT NULL CHECK ((JSON_VALID("derived_tags_json") OR "derived_tags_json" IS NULL)), "manual_overrides_json" text NOT NULL CHECK ((JSON_VALID("manual_overrides_json") OR "manual_overrides_json" IS NULL)), "normalizer_version" varchar(32) NOT NULL, "tag_rule_version" varchar(32) NOT NULL, "updated_at" datetime NOT NULL, "updated_by" varchar(255) NOT NULL, "latest_job_id" char(32) NULL REFERENCES "drawing_metadata_drawingmetadataextractionjob" ("id") DEFERRABLE INITIALLY DEFERRED, "drawing_id" char(32) NOT NULL REFERENCES "drawing_metadata_registereddrawing" ("id") DEFERRABLE INITIALLY DEFERRED, "extraction_mode" varchar(8) NOT NULL, "review_status" varchar(24) NOT NULL, "reviewed_at" datetime NULL, "reviewed_by" varchar(255) NOT NULL, CONSTRAINT "drawing_metadata_unique_snapshot_per_mode" UNIQUE ("drawing_id", "extraction_mode"));

CREATE TABLE "drawing_metadata_registereddrawing" ("id" char(32) NOT NULL PRIMARY KEY, "host_drawing_id" varchar(255) NOT NULL, "filename" varchar(255) NOT NULL, "source_path" varchar(1024) NOT NULL, "source_format" varchar(64) NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "source_content_sha256" varchar(64) NOT NULL);

CREATE INDEX "drawing_metadata_drawingmetadataauditlog_drawing_id_b0a25656" ON "drawing_metadata_drawingmetadataauditlog" ("drawing_id");

CREATE INDEX "drawing_metadata_drawingmetadataauditlog_extraction_mode_6966ba31" ON "drawing_metadata_drawingmetadataauditlog" ("extraction_mode");

CREATE INDEX "drawing_metadata_drawingmetadataextractionjob_drawing_id_386a4c23" ON "drawing_metadata_drawingmetadataextractionjob" ("drawing_id");

CREATE INDEX "drawing_metadata_drawingmetadataextractionjob_extraction_mode_f21543f1" ON "drawing_metadata_drawingmetadataextractionjob" ("extraction_mode");

CREATE INDEX "drawing_metadata_drawingmetadataextractionjob_extraction_profile_a682168e" ON "drawing_metadata_drawingmetadataextractionjob" ("extraction_profile");

CREATE INDEX "drawing_metadata_drawingmetadataextractionjob_lease_expires_at_82601976" ON "drawing_metadata_drawingmetadataextractionjob" ("lease_expires_at");

CREATE INDEX "drawing_metadata_drawingmetadataextractionjob_status_df188bbb" ON "drawing_metadata_drawingmetadataextractionjob" ("status");

CREATE INDEX "drawing_metadata_drawingmetadataextractionjob_worker_name_661c8642" ON "drawing_metadata_drawingmetadataextractionjob" ("worker_name");

CREATE INDEX "drawing_metadata_drawingmetadatasnapshot_drawing_id_7c946f0b" ON "drawing_metadata_drawingmetadatasnapshot" ("drawing_id");

CREATE INDEX "drawing_metadata_drawingmetadatasnapshot_extraction_mode_3073f2f8" ON "drawing_metadata_drawingmetadatasnapshot" ("extraction_mode");

CREATE INDEX "drawing_metadata_drawingmetadatasnapshot_latest_job_id_28f06624" ON "drawing_metadata_drawingmetadatasnapshot" ("latest_job_id");

CREATE INDEX "drawing_metadata_drawingmetadatasnapshot_review_status_40214715" ON "drawing_metadata_drawingmetadatasnapshot" ("review_status");

CREATE INDEX "drawing_metadata_registereddrawing_source_content_sha256_486f4047" ON "drawing_metadata_registereddrawing" ("source_content_sha256");
