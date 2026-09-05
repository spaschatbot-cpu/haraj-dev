-- بنية قاعدة v1 — الجداول وحدها، بلا صفٍّ واحد.
--
-- المصدر: نسخة الإنتاج التي سلّمها المالك في 2026-09-05 (MySQL 8.0.46،
-- `hara_clone_v1`، utf8mb4).
--
-- **والنسخة نفسها لا تدخل هذا المستودع ولا أي مستودع.** فيها أسماء 44,039
-- عميلاً وجوالاتهم وأرقام هويّاتهم، ومعها `userss.password` و`session_token`
-- و`remember_token_hash` و`verification_code`، وجدولا `settings` و
-- `app_settings` اللذان قد يحملان مفاتيح تكامل (المادة 5-3). وما يُرفع إلى
-- مستودعٍ بعيد لا يعود: يبقى في تاريخ git بعد الحذف. وهي 340 ميجابايت على
-- أي حال، وGitHub يرفض ما فوق 100.
--
-- وهذا الملفّ **بنيةٌ فقط**: 192 `CREATE TABLE` وصفر `INSERT`، مُستخرَجةً
-- بقراءةٍ متدفّقة تُبقي السطور من `CREATE TABLE` إلى قوس الإغلاق وتُسقط ما
-- عداها. ولا حرفيّةَ نصٍّ فيه إلا قيمُ `enum` وتعليقاتُ الأعمدة — وخلوّه من
-- الصفوف يحرسه `ops/checks/v1_fixture_matches_its_schema.py`.
--
-- ولماذا يُرفع أصلاً: خريطة الحقول (T303) والمستخرِج (T305) والبناة
-- (T306–T310) تحتاج **شكل** البيانات لا البيانات. وشكلٌ في المستودع يعني أن
-- من يكتب بانياً لا يحتاج نسخةً على قرصه.
--
-- والصفوف التجريبية في `v1-seed.sql` بجانبه، والجرد في `inventory.md`.

CREATE TABLE `vehicle_images` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `vehicle_id` int unsigned NOT NULL,
  `image_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `image_url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sort_order` int NOT NULL DEFAULT '0',
  `storage_disk` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_primary` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `image_blob` longblob,
  `image_mime` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_vehicle_images_vehicle_id` (`vehicle_id`),
  KEY `idx_vehicle_images_vehicle_sort` (`vehicle_id`,`sort_order`)
) ENGINE=InnoDB AUTO_INCREMENT=48344 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `payments_test` (
  `id` int NOT NULL AUTO_INCREMENT,
  `customer_id` int NOT NULL,
  `payment_code` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `amount` decimal(10,2) DEFAULT NULL,
  `payment_reference` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `odoo_payment_id` int DEFAULT NULL,
  `payment_name` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `state` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `status` enum('pending','sent','failed','approved','Canceled') CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci NOT NULL DEFAULT 'pending',
  `full_name` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `transfer_date` date DEFAULT NULL,
  `receipt_image_base64` longtext CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci,
  `moyasar_payment_id` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `attempts` int NOT NULL DEFAULT '0',
  `last_error` text CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci,
  PRIMARY KEY (`id`),
  UNIQUE KEY `moyasar_payment_id` (`moyasar_payment_id`),
  UNIQUE KEY `uq_moyasar_payment_id` (`moyasar_payment_id`),
  UNIQUE KEY `uniq_moyasar` (`moyasar_payment_id`),
  UNIQUE KEY `uniq_odoo_payment_id` (`odoo_payment_id`),
  KEY `idx_test_customer` (`customer_id`),
  KEY `idx_test_date` (`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=5893 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_unicode_ci;

CREATE TABLE `bids_backup_20260214` (
  `id` int NOT NULL AUTO_INCREMENT,
  `auction_id` int NOT NULL,
  `user_id` int NOT NULL,
  `amount` int NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `paid_amount` decimal(10,2) DEFAULT '0.00',
  `is_auto` tinyint(1) DEFAULT '0',
  `offer_status` enum('pending','accepted','rejected') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'pending',
  `sms_sent` tinyint(1) DEFAULT '0',
  `amount_with_vat` decimal(10,2) DEFAULT NULL,
  `auction_name` int DEFAULT NULL,
  `status` enum('active','not_active') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_auction_unique` (`user_id`,`auction_id`),
  KEY `bids_ibfk_1` (`auction_id`),
  KEY `bids_ibfk_2` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=158383 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `abubakr_20260805_bak_bids` (
  `id` int NOT NULL AUTO_INCREMENT,
  `auction_id` int NOT NULL,
  `user_id` int NOT NULL,
  `amount` int NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `paid_amount` decimal(10,2) DEFAULT '0.00',
  `is_auto` tinyint(1) DEFAULT '0',
  `offer_status` enum('pending','accepted','rejected') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'pending',
  `sms_sent` tinyint(1) DEFAULT '0',
  `amount_with_vat` decimal(10,2) DEFAULT NULL,
  `auction_name` int DEFAULT NULL,
  `status` enum('active','not_active','deleted') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `vehicle_id` int DEFAULT NULL,
  `rank` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `bids_ibfk_1` (`auction_id`),
  KEY `bids_ibfk_2` (`user_id`),
  KEY `idx_bids_vehicle` (`vehicle_id`),
  KEY `idx_bids_vehicle_rank` (`vehicle_id`,`rank`),
  KEY `idx_bids_vehicle_id` (`vehicle_id`),
  KEY `idx_bids_user_id` (`user_id`),
  KEY `idx_bids_vehicle_status_amount` (`vehicle_id`,`status`,`amount`),
  KEY `idx_bids_auction_status_amount` (`auction_id`,`status`,`amount`)
) ENGINE=InnoDB AUTO_INCREMENT=107121 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `abubakr_20260805_bak_deposits` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2686 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `account_page_settings` (
  `setting_key` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `setting_value` longtext COLLATE utf8mb4_unicode_ci,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`setting_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `admin_login_attempts` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `ip` varchar(45) NOT NULL,
  `username` varchar(190) NOT NULL,
  `attempts` int NOT NULL DEFAULT '0',
  `locked_until` datetime DEFAULT NULL,
  `last_attempt_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_ip_user` (`ip`,`username`),
  KEY `idx_locked` (`locked_until`)
) ENGINE=InnoDB AUTO_INCREMENT=376 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `admin_notifications` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `body` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `ref_table` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ref_id` bigint unsigned DEFAULT NULL,
  `is_read` tinyint(1) NOT NULL DEFAULT '0',
  `read_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_type` (`type`),
  KEY `idx_read` (`is_read`),
  KEY `idx_created` (`created_at`),
  KEY `idx_ref` (`ref_table`,`ref_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `admin_sections` (
  `id` int NOT NULL AUTO_INCREMENT,
  `section_key` varchar(64) NOT NULL,
  `name_ar` varchar(255) NOT NULL,
  `name_en` varchar(255) NOT NULL,
  `href` varchar(255) DEFAULT NULL,
  `description_ar` text,
  `description_en` text,
  `sort_order` int NOT NULL DEFAULT '100',
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `section_key` (`section_key`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `aftersales_hidden_auctions` (
  `auction_id` int NOT NULL,
  `hidden_by` varchar(100) DEFAULT NULL,
  `hidden_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`auction_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `amount` (
  `id` int NOT NULL AUTO_INCREMENT,
  `insurance_per_auction` int NOT NULL DEFAULT '1000',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `api_tokens` (
  `id` int NOT NULL AUTO_INCREMENT,
  `employee_id` int NOT NULL,
  `token` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `expires_at` datetime NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `last_used_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`),
  KEY `fk_token_employee` (`employee_id`),
  CONSTRAINT `fk_token_employee` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `app_meta` (
  `meta_key` varchar(80) NOT NULL,
  `meta_value` varchar(255) NOT NULL,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`meta_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `app_settings` (
  `skey` varchar(100) NOT NULL,
  `svalue` text,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`skey`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `attendance` (
  `id` int NOT NULL AUTO_INCREMENT,
  `employee_id` int NOT NULL,
  `date` date NOT NULL,
  `checkin_time` time DEFAULT NULL,
  `checkout_time` time DEFAULT NULL,
  `source` enum('mobile','admin') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'mobile',
  `qr_token` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `synced` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_attendance_day` (`employee_id`,`date`),
  CONSTRAINT `fk_att_employee` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `auction_campaigns` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `start_time` datetime DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `sms_reminder_time` datetime DEFAULT NULL,
  `general_settings` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_status` (`status`),
  KEY `idx_start_time` (`start_time`),
  CONSTRAINT `auction_campaigns_chk_1` CHECK (json_valid(`general_settings`))
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `auction_name` (
  `id` int NOT NULL AUTO_INCREMENT,
  `au_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `start` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `end` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `create_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `auction_park_logs` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `auction_id` int NOT NULL,
  `detail_id` int NOT NULL,
  `old_id_park` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `new_id_park` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `admin_username` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `admin_role` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `ip_address` varchar(45) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `user_agent` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_auction_id` (`auction_id`),
  KEY `idx_detail_id` (`detail_id`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `auction_translation_options` (
  `id` int NOT NULL AUTO_INCREMENT,
  `translation_id` int NOT NULL,
  `option_key` varchar(191) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `value_arabic` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `value_english` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `value_urdu` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `value_hindi` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `sort_order` int NOT NULL DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_trans_option` (`translation_id`,`option_key`),
  UNIQUE KEY `uq_trans_opt` (`translation_id`,`option_key`),
  CONSTRAINT `fk_topt_trans` FOREIGN KEY (`translation_id`) REFERENCES `auction_translations` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2858 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `auction_translations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `key_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `value_arabic` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `value_english` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `value_urdu` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `value_hindi` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `has_options` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_key_name` (`key_name`),
  KEY `idx_keyname` (`key_name`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `auction_vehicles` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `auction_id` int DEFAULT NULL,
  `campaign_id` int unsigned DEFAULT NULL,
  `lot_number` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `vehicle_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `make` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `model` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `year` int DEFAULT NULL,
  `starting_price` decimal(12,2) NOT NULL DEFAULT '0.00',
  `vehicle_condition` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Intact',
  `condition_notes` text COLLATE utf8mb4_unicode_ci,
  `vehicle_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `settings_override` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `override_settings` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT NULL,
  `vehicle_brand` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `year_of_manufacture` int DEFAULT NULL,
  `mileage` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `the_color` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Plate_number` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plate_type` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chassis_number` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `insurance_company` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `overview` text COLLATE utf8mb4_unicode_ci,
  `mvpi_status` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `auto_bid` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bidamount` decimal(12,2) DEFAULT NULL,
  `activation_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inspection_days` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `time_periods` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `preview_site` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `the_doors` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `the_weight` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `input_time` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inspection_report_media` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `winner_user_id` int DEFAULT NULL,
  `final_price` decimal(12,2) DEFAULT NULL,
  `winner_paid_at` datetime DEFAULT NULL,
  `payment_method` varchar(60) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transaction_ref` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `receipt_image_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `winning_bid_id` int DEFAULT NULL,
  `awarded_at` datetime DEFAULT NULL,
  `approval_status` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'pending=awaiting admin approval, approved=winner confirmed, rejected=admin rejected',
  `display_image` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fuel_type` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `runs_status` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `key_status` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_marketing` tinyint(1) NOT NULL DEFAULT '0',
  `partner_decision` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `partner_decision_bid_id` int DEFAULT NULL,
  `partner_decided_at` datetime DEFAULT NULL,
  `partner_decided_by` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `claim_number` varchar(60) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_auction_vehicles_auction_id` (`auction_id`),
  KEY `idx_auction_vehicles_status` (`status`),
  KEY `idx_av_marketing` (`is_marketing`,`auction_id`),
  KEY `idx_av_claim_number` (`claim_number`),
  CONSTRAINT `fk_auction_vehicles_auction` FOREIGN KEY (`auction_id`) REFERENCES `auctions` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `auction_vehicles_chk_1` CHECK (json_valid(`vehicle_data`)),
  CONSTRAINT `auction_vehicles_chk_2` CHECK (json_valid(`settings_override`)),
  CONSTRAINT `auction_vehicles_chk_3` CHECK (json_valid(`override_settings`))
) ENGINE=InnoDB AUTO_INCREMENT=13083 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `auction_vehicles_preend_20260606_185855` (
  `id` int unsigned NOT NULL DEFAULT '0',
  `auction_id` int DEFAULT NULL,
  `campaign_id` int unsigned DEFAULT NULL,
  `lot_number` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `vehicle_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `make` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `model` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `year` int DEFAULT NULL,
  `starting_price` decimal(12,2) NOT NULL DEFAULT '0.00',
  `vehicle_condition` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Intact',
  `condition_notes` text COLLATE utf8mb4_unicode_ci,
  `vehicle_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `settings_override` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `override_settings` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT NULL,
  `vehicle_brand` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `year_of_manufacture` int DEFAULT NULL,
  `mileage` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `the_color` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Plate_number` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chassis_number` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `insurance_company` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `overview` text COLLATE utf8mb4_unicode_ci,
  `mvpi_status` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `auto_bid` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bidamount` decimal(12,2) DEFAULT NULL,
  `activation_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inspection_days` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `time_periods` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `preview_site` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `the_doors` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `the_weight` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `input_time` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inspection_report_media` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `winner_user_id` int DEFAULT NULL,
  `final_price` decimal(12,2) DEFAULT NULL,
  `winner_paid_at` datetime DEFAULT NULL,
  `payment_method` varchar(60) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transaction_ref` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `receipt_image_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `winning_bid_id` int DEFAULT NULL,
  `awarded_at` datetime DEFAULT NULL,
  `approval_status` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'pending=awaiting admin approval, approved=winner confirmed, rejected=admin rejected',
  `display_image` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fuel_type` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `runs_status` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `key_status` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `auctions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name_of_auction` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `car_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `image` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `id_park` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mileage` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `starting_price` decimal(12,2) DEFAULT NULL,
  `increment` decimal(12,2) DEFAULT NULL,
  `start_time` datetime DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `status` enum('not_active','active','soon','later','coming','relater','upcoming','ended') COLLATE utf8mb4_unicode_ci DEFAULT 'not_active',
  `offer_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `type_auctions` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `vat_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fees` decimal(12,2) DEFAULT NULL,
  `share_count` int NOT NULL DEFAULT '0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `sms_reminder_time` datetime DEFAULT NULL,
  `is_mega_auction` tinyint(1) NOT NULL DEFAULT '0',
  `insurance_amount` decimal(10,2) NOT NULL DEFAULT '0.00',
  PRIMARY KEY (`id`),
  KEY `idx_auctions_status` (`status`),
  KEY `idx_auctions_is_mega_auction` (`is_mega_auction`),
  KEY `idx_auctions_end_time` (`end_time`),
  KEY `idx_auctions_status_end_time` (`status`,`end_time`)
) ENGINE=InnoDB AUTO_INCREMENT=1019 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `auctions_claims` (
  `id` int NOT NULL AUTO_INCREMENT,
  `car_id` int NOT NULL,
  `claim_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `registration_form` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_auctions_claims_car_id` (`car_id`)
) ENGINE=InnoDB AUTO_INCREMENT=7848 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `audit_log` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `actor_id` bigint DEFAULT NULL,
  `actor_username` varchar(190) DEFAULT NULL,
  `actor_role` varchar(50) DEFAULT NULL,
  `action_key` varchar(80) NOT NULL,
  `entity_type` varchar(80) DEFAULT NULL,
  `entity_id` varchar(80) DEFAULT NULL,
  `message` varchar(255) DEFAULT NULL,
  `ip` varchar(45) DEFAULT NULL,
  `user_agent` varchar(255) DEFAULT NULL,
  `meta` json DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_actor` (`actor_username`,`actor_role`),
  KEY `idx_action` (`action_key`),
  KEY `idx_entity` (`entity_type`,`entity_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `auto_bids` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `auction_id` int NOT NULL,
  `max_amount` decimal(10,2) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`,`auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=31 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `av_status_bak_20260602` (
  `id` int unsigned NOT NULL DEFAULT '0',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `bank_transfers` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `full_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `transfer_date` date NOT NULL,
  `receipt_image` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `amount` decimal(10,2) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `status` enum('pending','accpted','rejected') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'pending',
  PRIMARY KEY (`id`),
  KEY `fk_user` (`user_id`),
  CONSTRAINT `fk_user` FOREIGN KEY (`user_id`) REFERENCES `userss` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `bid_edit_audit` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `bid_id` int unsigned NOT NULL,
  `user_id` int unsigned NOT NULL,
  `auction_id` int unsigned NOT NULL,
  `vehicle_id` int unsigned DEFAULT NULL,
  `old_amount` decimal(15,2) NOT NULL DEFAULT '0.00',
  `new_amount` decimal(15,2) NOT NULL DEFAULT '0.00',
  `source` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'client',
  `actor_id` int unsigned DEFAULT NULL,
  `actor_name` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `edited_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_bid` (`bid_id`),
  KEY `idx_auction` (`auction_id`),
  KEY `idx_user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=18534 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `bids` (
  `id` int NOT NULL AUTO_INCREMENT,
  `auction_id` int NOT NULL,
  `user_id` int NOT NULL,
  `amount` int NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `paid_amount` decimal(10,2) DEFAULT '0.00',
  `is_auto` tinyint(1) DEFAULT '0',
  `offer_status` enum('pending','accepted','rejected') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'pending',
  `sms_sent` tinyint(1) DEFAULT '0',
  `amount_with_vat` decimal(10,2) DEFAULT NULL,
  `auction_name` int DEFAULT NULL,
  `status` enum('active','not_active','deleted') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `vehicle_id` int DEFAULT NULL,
  `rank` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `bids_ibfk_1` (`auction_id`),
  KEY `bids_ibfk_2` (`user_id`),
  KEY `idx_bids_vehicle` (`vehicle_id`),
  KEY `idx_bids_vehicle_rank` (`vehicle_id`,`rank`),
  KEY `idx_bids_vehicle_id` (`vehicle_id`),
  KEY `idx_bids_user_id` (`user_id`),
  KEY `idx_bids_vehicle_status_amount` (`vehicle_id`,`status`,`amount`),
  KEY `idx_bids_auction_status_amount` (`auction_id`,`status`,`amount`),
  CONSTRAINT `bids_ibfk_1` FOREIGN KEY (`auction_id`) REFERENCES `auctions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `bids_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `userss` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=133189 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `bids_backup_auction_name` (
  `id` int NOT NULL DEFAULT '0',
  `auction_id` int NOT NULL,
  `auction_name` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `bids_bak_20260812_152428_nidal` (
  `id` int NOT NULL DEFAULT '0',
  `auction_id` int NOT NULL,
  `user_id` int NOT NULL,
  `amount` int NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `paid_amount` decimal(10,2) DEFAULT '0.00',
  `is_auto` tinyint(1) DEFAULT '0',
  `offer_status` enum('pending','accepted','rejected') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'pending',
  `sms_sent` tinyint(1) DEFAULT '0',
  `amount_with_vat` decimal(10,2) DEFAULT NULL,
  `auction_name` int DEFAULT NULL,
  `status` enum('active','not_active','deleted') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `vehicle_id` int DEFAULT NULL,
  `rank` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `bids_bak_20260821_143655_mahmoud` (
  `id` int NOT NULL DEFAULT '0',
  `auction_id` int NOT NULL,
  `user_id` int NOT NULL,
  `amount` int NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `paid_amount` decimal(10,2) DEFAULT '0.00',
  `is_auto` tinyint(1) DEFAULT '0',
  `offer_status` enum('pending','accepted','rejected') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'pending',
  `sms_sent` tinyint(1) DEFAULT '0',
  `amount_with_vat` decimal(10,2) DEFAULT NULL,
  `auction_name` int DEFAULT NULL,
  `status` enum('active','not_active','deleted') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `vehicle_id` int DEFAULT NULL,
  `rank` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `bids_preend_20260606_185855` (
  `id` int NOT NULL DEFAULT '0',
  `auction_id` int NOT NULL,
  `user_id` int NOT NULL,
  `amount` int NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `paid_amount` decimal(10,2) DEFAULT '0.00',
  `is_auto` tinyint(1) DEFAULT '0',
  `offer_status` enum('pending','accepted','rejected') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'pending',
  `sms_sent` tinyint(1) DEFAULT '0',
  `amount_with_vat` decimal(10,2) DEFAULT NULL,
  `auction_name` int DEFAULT NULL,
  `status` enum('active','not_active') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `vehicle_id` int DEFAULT NULL,
  `rank` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `car_images` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_details` int NOT NULL,
  `image` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `uploaded_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `id_details` (`id_details`),
  CONSTRAINT `fk_id_details` FOREIGN KEY (`id_details`) REFERENCES `details` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=93656 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `card_permissions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `card_key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `role` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `allowed` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_card_role` (`card_key`,`role`)
) ENGINE=InnoDB AUTO_INCREMENT=1202 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `cards` (
  `id` int NOT NULL AUTO_INCREMENT,
  `card_key` varchar(100) NOT NULL,
  `parent_key` varchar(100) DEFAULT NULL,
  `section_key` varchar(64) DEFAULT NULL,
  `title_ar` varchar(150) NOT NULL,
  `title_en` varchar(150) DEFAULT NULL,
  `href` varchar(255) DEFAULT NULL,
  `desc_ar` varchar(255) DEFAULT NULL,
  `desc_en` varchar(255) DEFAULT NULL,
  `sort_order` int NOT NULL DEFAULT '100',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `card_key` (`card_key`),
  UNIQUE KEY `uniq_card_key` (`card_key`),
  KEY `idx_cards_section_key` (`section_key`),
  KEY `idx_parent` (`parent_key`)
) ENGINE=InnoDB AUTO_INCREMENT=4739686 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `categories` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `image` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `link` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `status` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `chat_agent_departments` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `agent_id` int unsigned NOT NULL,
  `department_id` int unsigned NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_agent_dept` (`agent_id`,`department_id`),
  KEY `fk_ad_dept` (`department_id`),
  CONSTRAINT `fk_ad_agent` FOREIGN KEY (`agent_id`) REFERENCES `chat_agents` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ad_dept` FOREIGN KEY (`department_id`) REFERENCES `chat_departments` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `chat_agents` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int unsigned DEFAULT NULL,
  `name` varchar(190) NOT NULL,
  `phone` varchar(50) DEFAULT NULL,
  `email` varchar(190) DEFAULT NULL,
  `is_online` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `chat_conversations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `client_name` varchar(100) DEFAULT NULL,
  `client_phone` varchar(30) DEFAULT NULL,
  `client_email` varchar(150) DEFAULT NULL,
  `dept_id` int NOT NULL DEFAULT '0',
  `staff_id` int DEFAULT NULL,
  `status` enum('open','closed') DEFAULT 'open',
  `client_token` varchar(64) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `staff_id` (`staff_id`)
) ENGINE=InnoDB AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `chat_departments` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `dept_key` varchar(50) NOT NULL,
  `name_ar` varchar(190) NOT NULL,
  `name_en` varchar(190) NOT NULL,
  `is_online` tinyint(1) NOT NULL DEFAULT '1',
  `use_ai` tinyint(1) NOT NULL DEFAULT '0',
  `sort_order` int unsigned NOT NULL DEFAULT '100',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `dept_key` (`dept_key`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `chat_messages` (
  `id` int NOT NULL AUTO_INCREMENT,
  `conv_id` int NOT NULL,
  `sender_type` enum('client','staff') NOT NULL,
  `body` text,
  `attachment_path` varchar(255) DEFAULT NULL,
  `attachment_name` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `conv_id` (`conv_id`),
  CONSTRAINT `fk_msg_conv` FOREIGN KEY (`conv_id`) REFERENCES `chat_conversations` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=30 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `chat_ratings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `conv_id` int NOT NULL,
  `staff_id` int DEFAULT NULL,
  `rating` tinyint NOT NULL,
  `comment` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `stars` tinyint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_conv` (`conv_id`),
  KEY `staff_id` (`staff_id`),
  CONSTRAINT `fk_rate_conv` FOREIGN KEY (`conv_id`) REFERENCES `chat_conversations` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_rate_staff` FOREIGN KEY (`staff_id`) REFERENCES `staff` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `chat_sessions` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int unsigned DEFAULT NULL,
  `guest_name` varchar(190) DEFAULT NULL,
  `session_token` varchar(64) NOT NULL,
  `department_id` int unsigned DEFAULT NULL,
  `lang` varchar(5) NOT NULL DEFAULT 'ar',
  `status` enum('open','closed') NOT NULL DEFAULT 'open',
  `rating` tinyint unsigned DEFAULT NULL,
  `feedback` text,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `closed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `session_token` (`session_token`),
  KEY `fk_session_dept` (`department_id`),
  CONSTRAINT `fk_session_dept` FOREIGN KEY (`department_id`) REFERENCES `chat_departments` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `chat_typing` (
  `conv_id` int NOT NULL,
  `who` enum('client','staff') NOT NULL,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`conv_id`,`who`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `companies` (
  `id` int NOT NULL AUTO_INCREMENT,
  `company_name` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `author_name` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `id_number` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `phone` int NOT NULL,
  `country` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `city` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `reigaon` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `bulding` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `add_number` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `vat_number` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `image1` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `image2` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `image3` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `image4` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `company_payment` (
  `id` int NOT NULL AUTO_INCREMENT,
  `claim_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `car_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `plate_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `model` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `chassis_number` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `net_compensation` decimal(10,2) NOT NULL,
  `percentage` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `amount_before_tax` decimal(10,2) NOT NULL,
  `tax_amount` decimal(10,2) NOT NULL,
  `total_with_tax` decimal(10,2) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=169 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `conversation_ratings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `conv_id` int NOT NULL,
  `rating` tinyint NOT NULL,
  `comment` varchar(500) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_conv` (`conv_id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `conversations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `dept_id` int DEFAULT NULL,
  `assigned_staff_id` int DEFAULT NULL,
  `client_name` varchar(100) DEFAULT NULL,
  `client_phone` varchar(20) DEFAULT NULL,
  `client_email` varchar(150) DEFAULT NULL,
  `client_lang` varchar(5) DEFAULT NULL,
  `client_session` varchar(64) DEFAULT NULL,
  `client_token` varchar(64) DEFAULT NULL,
  `status` enum('open','pending','closed') NOT NULL DEFAULT 'open',
  `started_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `ended_at` timestamp NULL DEFAULT NULL,
  `last_activity_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `dept_id` (`dept_id`),
  KEY `assigned_staff_id` (`assigned_staff_id`),
  KEY `status` (`status`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `customer_features` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `id_customer` bigint unsigned NOT NULL,
  `voice_auction` tinyint(1) NOT NULL DEFAULT '0',
  `merchants_auction` tinyint(1) NOT NULL DEFAULT '0',
  `note` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_id_customer` (`id_customer`),
  KEY `idx_voice` (`voice_auction`),
  KEY `idx_merchants` (`merchants_auction`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `customer_links` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `odoo_customer_id` int NOT NULL,
  `user_id` int NOT NULL,
  `source` varchar(16) NOT NULL,
  `confidence` varchar(12) NOT NULL DEFAULT 'confirmed',
  `note` varchar(255) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_pair` (`odoo_customer_id`,`user_id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_customer` (`odoo_customer_id`),
  KEY `idx_confidence` (`confidence`)
) ENGINE=InnoDB AUTO_INCREMENT=14710 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `delivery_requests` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int unsigned NOT NULL,
  `recipient_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `order_date` date NOT NULL,
  `receive_time` datetime NOT NULL,
  `delivery_location` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `location_coords` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `status_note` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_delivery_user_id` (`user_id`),
  KEY `idx_delivery_status` (`status`),
  KEY `idx_delivery_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `departments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `slug` varchar(50) NOT NULL,
  `label` varchar(100) NOT NULL,
  `is_online` tinyint(1) NOT NULL DEFAULT '0',
  `last_seen` timestamp NULL DEFAULT NULL,
  `note` varchar(255) DEFAULT NULL,
  `preferred_channel` enum('whatsapp','livechat','tel','anchor') NOT NULL DEFAULT 'whatsapp',
  `wa_number` varchar(20) DEFAULT NULL,
  `tel_number` varchar(20) DEFAULT NULL,
  `livechat_url` varchar(255) DEFAULT NULL,
  `responsible_id` int DEFAULT NULL,
  `updated_by` varchar(100) DEFAULT NULL,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `slug` (`slug`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `dept_status` (
  `id` int NOT NULL AUTO_INCREMENT,
  `dept` enum('support','sales','accounts','transport') NOT NULL,
  `label` varchar(100) NOT NULL,
  `is_online` tinyint(1) NOT NULL DEFAULT '0',
  `last_seen` timestamp NULL DEFAULT NULL,
  `note` varchar(255) DEFAULT NULL,
  `updated_by` varchar(100) DEFAULT NULL,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `dept` (`dept`)
) ENGINE=InnoDB AUTO_INCREMENT=157 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `details` (
  `id` int NOT NULL AUTO_INCREMENT,
  `car_id` int NOT NULL,
  `overview` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `vehicle_brand` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `model` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mvpi_status` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `year_of_manufacture` int DEFAULT NULL,
  `chassis_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `the_color` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `the_doors` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'لايوجد',
  `the_condition` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `the_weight` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `inspection_days` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `time_periods` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `preview_site` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inspection_report_media` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `insurance_company` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `input_time` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `activation_status` enum('active','not active','soon') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'not active',
  `Plate_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `bidamount` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `auto_bid` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `car_id` (`car_id`),
  KEY `idx_details_car_id` (`car_id`),
  KEY `idx_details_vehicle_brand` (`vehicle_brand`),
  KEY `idx_details_plate` (`Plate_number`),
  KEY `idx_details_chassis` (`chassis_number`),
  KEY `idx_details_year` (`year_of_manufacture`),
  CONSTRAINT `details_ibfk_1` FOREIGN KEY (`car_id`) REFERENCES `auctions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=8805 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `employees` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `phone` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `email` varchar(120) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `password_hash` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` enum('admin','employee') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'employee',
  `status` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `api_token_hash` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `api_token_expires` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `phone` (`phone`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `favorites` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `auction_id` int NOT NULL,
  `vehicle_id` int DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_user_auction_vehicle` (`user_id`,`auction_id`,`vehicle_id`),
  KEY `idx_fav_user_vehicle` (`user_id`,`vehicle_id`)
) ENGINE=InnoDB AUTO_INCREMENT=34417 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `fcm_tokens` (
  `id` int NOT NULL AUTO_INCREMENT,
  `token` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `files` (
  `id` int NOT NULL AUTO_INCREMENT,
  `file_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `file_path` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `file_size` int NOT NULL,
  `file_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `uploaded_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `firebase_tokens` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `phone` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `token` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `platform` enum('android','ios') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'android',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `fix68_bak_deposits` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2668 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `haraj_chat_agents` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `username` varchar(60) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `department_id` int NOT NULL,
  `is_online` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  KEY `department_id` (`department_id`),
  CONSTRAINT `haraj_chat_agents_ibfk_1` FOREIGN KEY (`department_id`) REFERENCES `haraj_chat_departments` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `haraj_chat_conversations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `session_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` int DEFAULT NULL,
  `user_name` varchar(190) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `department_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `staff_id` bigint unsigned DEFAULT NULL,
  `lang` char(2) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'ar',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `closed_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_conv_staff` (`staff_id`),
  CONSTRAINT `fk_conv_staff` FOREIGN KEY (`staff_id`) REFERENCES `haraj_chat_staff` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=93296 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `haraj_chat_departments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `name_ar` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `name_en` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_online` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `haraj_chat_messages` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `session_id` bigint unsigned DEFAULT NULL,
  `sender_type` enum('user','bot','staff') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'user',
  `sender_id` bigint unsigned DEFAULT NULL,
  `message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `department_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_read` tinyint(1) NOT NULL DEFAULT '0',
  `conversation_id` bigint NOT NULL,
  `sender` enum('user','bot','agent') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `message_text` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `lang` char(2) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'ar',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `conversation_id` (`conversation_id`),
  KEY `idx_session_id` (`session_id`),
  KEY `idx_department_code` (`department_code`),
  KEY `idx_is_read` (`is_read`),
  CONSTRAINT `haraj_chat_messages_ibfk_1` FOREIGN KEY (`conversation_id`) REFERENCES `haraj_chat_conversations` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=93269 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `haraj_chat_notifications` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `conversation_id` bigint NOT NULL,
  `is_read` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `conversation_id` (`conversation_id`),
  CONSTRAINT `haraj_chat_notifications_ibfk_1` FOREIGN KEY (`conversation_id`) REFERENCES `haraj_chat_conversations` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `haraj_chat_ratings` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `conversation_id` bigint NOT NULL,
  `rating` tinyint NOT NULL,
  `comment` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `conversation_id` (`conversation_id`),
  CONSTRAINT `haraj_chat_ratings_ibfk_1` FOREIGN KEY (`conversation_id`) REFERENCES `haraj_chat_conversations` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `haraj_chat_sessions` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `session_token` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `user_id` bigint unsigned DEFAULT NULL,
  `user_name` varchar(190) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `language` varchar(5) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'ar',
  `department_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `status` enum('open','closed') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'open',
  `rating` tinyint unsigned DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  `last_message_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_session_token` (`session_token`),
  KEY `idx_department` (`department_code`),
  KEY `idx_dept_last` (`department_code`,`last_message_at`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_session_department` FOREIGN KEY (`department_code`) REFERENCES `haraj_departments` (`code`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `haraj_chat_staff` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `username` varchar(100) NOT NULL,
  `full_name` varchar(190) NOT NULL,
  `password_hash` varchar(255) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `is_online` tinyint(1) NOT NULL DEFAULT '0',
  `manual_online` tinyint(1) NOT NULL DEFAULT '0',
  `work_start` time NOT NULL DEFAULT '09:00:00',
  `work_end` time NOT NULL DEFAULT '17:00:00',
  `last_seen` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `haraj_chat_staff_departments` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `staff_id` bigint unsigned NOT NULL,
  `department_code` varchar(50) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_staff_dept` (`staff_id`,`department_code`),
  CONSTRAINT `fk_staff_dept_staff` FOREIGN KEY (`staff_id`) REFERENCES `haraj_chat_staff` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `haraj_conversation_meta` (
  `conversation_id` bigint NOT NULL,
  `assigned_staff_id` int unsigned DEFAULT NULL,
  `rating` tinyint DEFAULT NULL,
  `rated_at` datetime DEFAULT NULL,
  `closed_by_admin_id` int DEFAULT NULL,
  `closed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`conversation_id`),
  KEY `idx_meta_staff` (`assigned_staff_id`),
  KEY `idx_meta_rating` (`rating`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `haraj_departments` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `name_ar` varchar(190) NOT NULL,
  `name_en` varchar(190) NOT NULL,
  `is_online` tinyint(1) NOT NULL DEFAULT '1',
  `sort_order` int NOT NULL DEFAULT '0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_code` (`code`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `haraj_staff` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL,
  `full_name` varchar(190) NOT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `department_code` varchar(50) NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `work_start` time NOT NULL DEFAULT '09:00:00',
  `work_end` time NOT NULL DEFAULT '17:00:00',
  `is_online` tinyint(1) NOT NULL DEFAULT '0',
  `last_seen` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_staff_username` (`username`),
  KEY `idx_staff_department` (`department_code`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `haraj_support_tickets` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `department` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'support',
  `priority` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'normal',
  `subject` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `message` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'open',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_haraj_support_user_id` (`user_id`),
  KEY `idx_haraj_support_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `hehewala` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_userss` int DEFAULT NULL,
  `sender_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `phone` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `receipt_image` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` tinyint(1) DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_id_userss` (`id_userss`),
  CONSTRAINT `fk_id_userss` FOREIGN KEY (`id_userss`) REFERENCES `userss` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `home_showcase` (
  `id` int NOT NULL AUTO_INCREMENT,
  `type` enum('carousel','single','most_viewed') NOT NULL DEFAULT 'carousel',
  `title_ar` varchar(150) DEFAULT NULL,
  `title_en` varchar(150) DEFAULT NULL,
  `params` text,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `home_showcase_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `showcase_id` int NOT NULL,
  `image` varchar(255) NOT NULL,
  `link` varchar(255) DEFAULT NULL,
  `caption` varchar(255) DEFAULT NULL,
  `sort_order` int NOT NULL DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `showcase_id` (`showcase_id`),
  CONSTRAINT `home_showcase_items_ibfk_1` FOREIGN KEY (`showcase_id`) REFERENCES `home_showcase` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `insurance_cars` (
  `id` int NOT NULL,
  `car_name` varchar(255) DEFAULT NULL,
  `model_year` int DEFAULT NULL,
  `chassis_no` varchar(100) DEFAULT NULL,
  `color` varchar(50) DEFAULT NULL,
  `plate_no` varchar(100) DEFAULT NULL,
  `claim_no` varchar(100) DEFAULT NULL,
  `insurance_company` varchar(255) DEFAULT NULL,
  `card_image` varchar(255) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `insurance_companies` (
  `id` int NOT NULL AUTO_INCREMENT,
  `company_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `insurance_deposits` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `void_reason` varchar(24) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`),
  KEY `idx_void_reason` (`void_reason`)
) ENGINE=InnoDB AUTO_INCREMENT=3209 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `insurance_deposits_bak_20260620` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=471 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `insurance_deposits_bak_20260716_165410` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2090 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `insurance_deposits_bak_20260717_190209` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2133 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `insurance_deposits_bak_20260725_ajlan` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1405 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `insurance_deposits_bak_20260725_muheet` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2528 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `insurance_deposits_bak_20260726_athyah` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1994 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `insurance_deposits_bak_20260726_overdebit` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2541 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `insurance_deposits_bak_20260728_duplocks` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2500 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `insurance_deposits_bak_20260729_missed2` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2309 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `insurance_deposits_bak_20260729_msuliman` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1456 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `insurance_deposits_bak_20260729_odoo_withdraw` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2551 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `insurance_deposits_bak_20260812_151258_release3` (
  `id` int unsigned NOT NULL DEFAULT '0',
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `insurance_deposits_bak_20260812_152428_nidal` (
  `id` int unsigned NOT NULL DEFAULT '0',
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `insurance_deposits_bak_20260820_144954_voidreason` (
  `id` int unsigned NOT NULL DEFAULT '0',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `notes` text COLLATE utf8mb4_unicode_ci
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `insurance_deposits_bak_20260820_154246_dupacct` (
  `id` int unsigned NOT NULL DEFAULT '0',
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `void_reason` varchar(24) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `insurance_deposits_bak_20260821_143655_mahmoud` (
  `id` int unsigned NOT NULL DEFAULT '0',
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `void_reason` varchar(24) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `insurance_deposits_fix_bak_20260718` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2492 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `insurance_deposits_preend_20260606_185855` (
  `id` int unsigned NOT NULL DEFAULT '0',
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `insurance_payments` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `auction_id` int NOT NULL,
  `amount` decimal(10,2) NOT NULL DEFAULT '0.00',
  `status` enum('active','refunded','used') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active',
  `paid_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `refunded_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_ip_user_auction` (`user_id`,`auction_id`),
  KEY `idx_ip_auction_id` (`auction_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `insurance_refund_shortfalls` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `refund_id` int NOT NULL,
  `user_id` int NOT NULL,
  `odoo_payment_id` varchar(64) DEFAULT NULL,
  `amount` decimal(12,2) NOT NULL,
  `resolved_amount` decimal(12,2) NOT NULL DEFAULT '0.00',
  `status` varchar(16) NOT NULL DEFAULT 'open',
  `reason` text,
  `detected_at` datetime NOT NULL,
  `last_checked_at` datetime DEFAULT NULL,
  `resolved_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_refund` (`refund_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `invoices` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `invoice_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `issue_date` datetime NOT NULL,
  `total_amount` decimal(10,2) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `payment_status` enum('غير مدفوع','مدفوع','دفع جزئي') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'غير مدفوع',
  `amount_paid` decimal(10,2) DEFAULT '0.00',
  `remaining_amount` decimal(10,2) GENERATED ALWAYS AS ((`total_amount` - `amount_paid`)) STORED,
  `auction_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `invoice_number` (`invoice_number`),
  KEY `user_id` (`user_id`),
  KEY `fk_auction` (`auction_id`),
  CONSTRAINT `fk_auction` FOREIGN KEY (`auction_id`) REFERENCES `auctions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `invoices_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `userss` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `invoices_oddo1` (
  `id` int NOT NULL AUTO_INCREMENT,
  `customer_name` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `vat_number` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `mobile` varchar(20) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `email` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `address` text CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci,
  `car_model` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `car_color` varchar(30) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `plate_no` varchar(20) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `amount` decimal(10,2) DEFAULT NULL,
  `odoo_invoice_id` int DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `transfer_image` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `status` enum('pending','paid','refunded') CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT 'pending',
  `auction_id` int DEFAULT NULL,
  `id_user` int DEFAULT NULL,
  `type_of_account` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_user_invoice` (`id_user`),
  CONSTRAINT `fk_user_invoice` FOREIGN KEY (`id_user`) REFERENCES `userss` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `invoices_odoo` (
  `id` int NOT NULL AUTO_INCREMENT,
  `invoice_id` int DEFAULT NULL,
  `customer_id` int DEFAULT NULL,
  `auction_id` int DEFAULT NULL,
  `car_plate` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `car_model` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `car_color` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `vehicle_brand` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `chasis_number` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `amount` decimal(10,2) DEFAULT NULL,
  `status` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `invoice_number` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `id_user` int DEFAULT NULL,
  `PaymentStatus` enum('not paid','paid','partially paid','reversed','draft','posted','cancelled') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'not paid',
  `fees_amount` decimal(10,2) NOT NULL DEFAULT '0.00',
  `total` decimal(12,2) DEFAULT NULL,
  `source` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `odoo_record_id` int DEFAULT NULL,
  `vehicle_id` int DEFAULT NULL,
  `amount_residual` decimal(12,2) DEFAULT NULL COMMENT 'Odoo amount_residual — authoritative remaining balance',
  PRIMARY KEY (`id`),
  KEY `fk_invoices_user` (`id_user`),
  KEY `idx_invoice_customer` (`customer_id`),
  KEY `idx_invoice_date` (`created_at`),
  KEY `idx_invoice_paid_number` (`PaymentStatus`,`invoice_number`),
  KEY `idx_invoice_user` (`id_user`),
  KEY `idx_invoice_created` (`created_at`),
  KEY `idx_inv_vehicle` (`vehicle_id`),
  KEY `idx_inv_source` (`source`),
  KEY `idx_invoices_odoo_source` (`source`),
  KEY `idx_odoo_record_id` (`odoo_record_id`),
  CONSTRAINT `fk_invoices_user` FOREIGN KEY (`id_user`) REFERENCES `userss` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=13117 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `invoices_odoo2` (
  `id` int NOT NULL AUTO_INCREMENT,
  `invoice_id` int DEFAULT NULL,
  `customer_id` int DEFAULT NULL,
  `auction_id` int DEFAULT NULL,
  `car_plate` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `car_model` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `car_color` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `vehicle_brand` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `chasis_number` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `amount` decimal(10,2) DEFAULT NULL,
  `purchase_price` decimal(10,2) DEFAULT NULL,
  `status` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `invoice_number` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `id_user` int DEFAULT NULL,
  `PaymentStatus` enum('not paid','paid','partially paid','reversed','draft','posted','cancelled') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'not paid',
  PRIMARY KEY (`id`),
  KEY `idx_car_plate` (`car_plate`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `invoices_odoo_bak_20260620` (
  `id` int NOT NULL AUTO_INCREMENT,
  `invoice_id` int DEFAULT NULL,
  `customer_id` int DEFAULT NULL,
  `auction_id` int DEFAULT NULL,
  `car_plate` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `car_model` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `car_color` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `vehicle_brand` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `chasis_number` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `amount` decimal(10,2) DEFAULT NULL,
  `status` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `invoice_number` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `id_user` int DEFAULT NULL,
  `PaymentStatus` enum('not paid','paid','partially paid','reversed','draft','posted','cancelled') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'not paid',
  `fees_amount` decimal(10,2) NOT NULL DEFAULT '0.00',
  `total` decimal(12,2) DEFAULT NULL,
  `source` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `odoo_record_id` int DEFAULT NULL,
  `vehicle_id` int DEFAULT NULL,
  `amount_residual` decimal(12,2) DEFAULT NULL COMMENT 'Odoo amount_residual — authoritative remaining balance',
  PRIMARY KEY (`id`),
  KEY `fk_invoices_user` (`id_user`),
  KEY `idx_invoice_customer` (`customer_id`),
  KEY `idx_invoice_date` (`created_at`),
  KEY `idx_invoice_paid_number` (`PaymentStatus`,`invoice_number`),
  KEY `idx_invoice_user` (`id_user`),
  KEY `idx_invoice_created` (`created_at`),
  KEY `idx_inv_vehicle` (`vehicle_id`),
  KEY `idx_inv_source` (`source`),
  KEY `idx_invoices_odoo_source` (`source`),
  KEY `idx_odoo_record_id` (`odoo_record_id`)
) ENGINE=InnoDB AUTO_INCREMENT=8488 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `invoices_odoo_bak_20260728_backfill` (
  `id` int NOT NULL AUTO_INCREMENT,
  `invoice_id` int DEFAULT NULL,
  `customer_id` int DEFAULT NULL,
  `auction_id` int DEFAULT NULL,
  `car_plate` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `car_model` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `car_color` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `vehicle_brand` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `chasis_number` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `amount` decimal(10,2) DEFAULT NULL,
  `status` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `invoice_number` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `id_user` int DEFAULT NULL,
  `PaymentStatus` enum('not paid','paid','partially paid','reversed','draft','posted','cancelled') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'not paid',
  `fees_amount` decimal(10,2) NOT NULL DEFAULT '0.00',
  `total` decimal(12,2) DEFAULT NULL,
  `source` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `odoo_record_id` int DEFAULT NULL,
  `vehicle_id` int DEFAULT NULL,
  `amount_residual` decimal(12,2) DEFAULT NULL COMMENT 'Odoo amount_residual — authoritative remaining balance',
  PRIMARY KEY (`id`),
  KEY `fk_invoices_user` (`id_user`),
  KEY `idx_invoice_customer` (`customer_id`),
  KEY `idx_invoice_date` (`created_at`),
  KEY `idx_invoice_paid_number` (`PaymentStatus`,`invoice_number`),
  KEY `idx_invoice_user` (`id_user`),
  KEY `idx_invoice_created` (`created_at`),
  KEY `idx_inv_vehicle` (`vehicle_id`),
  KEY `idx_inv_source` (`source`),
  KEY `idx_invoices_odoo_source` (`source`),
  KEY `idx_odoo_record_id` (`odoo_record_id`)
) ENGINE=InnoDB AUTO_INCREMENT=11563 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `invoices_odoo_bak_20260801_stale` (
  `id` int NOT NULL AUTO_INCREMENT,
  `invoice_id` int DEFAULT NULL,
  `customer_id` int DEFAULT NULL,
  `auction_id` int DEFAULT NULL,
  `car_plate` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `car_model` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `car_color` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `vehicle_brand` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `chasis_number` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `amount` decimal(10,2) DEFAULT NULL,
  `status` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `invoice_number` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `id_user` int DEFAULT NULL,
  `PaymentStatus` enum('not paid','paid','partially paid','reversed','draft','posted','cancelled') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'not paid',
  `fees_amount` decimal(10,2) NOT NULL DEFAULT '0.00',
  `total` decimal(12,2) DEFAULT NULL,
  `source` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `odoo_record_id` int DEFAULT NULL,
  `vehicle_id` int DEFAULT NULL,
  `amount_residual` decimal(12,2) DEFAULT NULL COMMENT 'Odoo amount_residual — authoritative remaining balance',
  PRIMARY KEY (`id`),
  KEY `fk_invoices_user` (`id_user`),
  KEY `idx_invoice_customer` (`customer_id`),
  KEY `idx_invoice_date` (`created_at`),
  KEY `idx_invoice_paid_number` (`PaymentStatus`,`invoice_number`),
  KEY `idx_invoice_user` (`id_user`),
  KEY `idx_invoice_created` (`created_at`),
  KEY `idx_inv_vehicle` (`vehicle_id`),
  KEY `idx_inv_source` (`source`),
  KEY `idx_invoices_odoo_source` (`source`),
  KEY `idx_odoo_record_id` (`odoo_record_id`)
) ENGINE=InnoDB AUTO_INCREMENT=7924 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `invoices_odoo_deleted_bak` (
  `id` int NOT NULL AUTO_INCREMENT,
  `invoice_id` int DEFAULT NULL,
  `customer_id` int DEFAULT NULL,
  `auction_id` int DEFAULT NULL,
  `car_plate` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `car_model` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `car_color` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `vehicle_brand` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `chasis_number` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `amount` decimal(10,2) DEFAULT NULL,
  `status` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `invoice_number` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `id_user` int DEFAULT NULL,
  `PaymentStatus` enum('not paid','paid','partially paid','reversed','draft','posted','cancelled') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'not paid',
  `fees_amount` decimal(10,2) NOT NULL DEFAULT '0.00',
  `total` decimal(12,2) DEFAULT NULL,
  `source` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `odoo_record_id` int DEFAULT NULL,
  `vehicle_id` int DEFAULT NULL,
  `amount_residual` decimal(12,2) DEFAULT NULL COMMENT 'Odoo amount_residual — authoritative remaining balance',
  PRIMARY KEY (`id`),
  KEY `fk_invoices_user` (`id_user`),
  KEY `idx_invoice_customer` (`customer_id`),
  KEY `idx_invoice_date` (`created_at`),
  KEY `idx_invoice_paid_number` (`PaymentStatus`,`invoice_number`),
  KEY `idx_invoice_user` (`id_user`),
  KEY `idx_invoice_created` (`created_at`),
  KEY `idx_inv_vehicle` (`vehicle_id`),
  KEY `idx_inv_source` (`source`),
  KEY `idx_invoices_odoo_source` (`source`),
  KEY `idx_odoo_record_id` (`odoo_record_id`)
) ENGINE=InnoDB AUTO_INCREMENT=10131 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `invoices_odoo_late_dupe_purge_20260607` (
  `id` int NOT NULL AUTO_INCREMENT,
  `invoice_id` int DEFAULT NULL,
  `customer_id` int DEFAULT NULL,
  `auction_id` int DEFAULT NULL,
  `car_plate` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `car_model` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `car_color` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `vehicle_brand` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `chasis_number` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `amount` decimal(10,2) DEFAULT NULL,
  `status` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `invoice_number` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `id_user` int DEFAULT NULL,
  `PaymentStatus` enum('not paid','paid','partially paid','reversed','draft','posted','cancelled') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'not paid',
  `fees_amount` decimal(10,2) NOT NULL DEFAULT '0.00',
  `total` decimal(12,2) DEFAULT NULL,
  `source` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `odoo_record_id` int DEFAULT NULL,
  `vehicle_id` int DEFAULT NULL,
  `amount_residual` decimal(12,2) DEFAULT NULL COMMENT 'Odoo amount_residual — authoritative remaining balance',
  PRIMARY KEY (`id`),
  KEY `fk_invoices_user` (`id_user`),
  KEY `idx_invoice_customer` (`customer_id`),
  KEY `idx_invoice_date` (`created_at`),
  KEY `idx_invoice_paid_number` (`PaymentStatus`,`invoice_number`),
  KEY `idx_invoice_user` (`id_user`),
  KEY `idx_invoice_created` (`created_at`),
  KEY `idx_inv_vehicle` (`vehicle_id`),
  KEY `idx_inv_source` (`source`),
  KEY `idx_invoices_odoo_source` (`source`),
  KEY `idx_odoo_record_id` (`odoo_record_id`)
) ENGINE=InnoDB AUTO_INCREMENT=9229 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `invoices_odoo_loopbak_20260606` (
  `id` int NOT NULL DEFAULT '0',
  `invoice_id` int DEFAULT NULL,
  `customer_id` int DEFAULT NULL,
  `auction_id` int DEFAULT NULL,
  `car_plate` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `car_model` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `car_color` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `vehicle_brand` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `chasis_number` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `amount` decimal(10,2) DEFAULT NULL,
  `status` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `invoice_number` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `id_user` int DEFAULT NULL,
  `PaymentStatus` enum('not paid','paid','partially paid','reversed','draft','posted','cancelled') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'not paid',
  `fees_amount` decimal(10,2) NOT NULL DEFAULT '0.00',
  `total` decimal(12,2) DEFAULT NULL,
  `source` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `odoo_record_id` int DEFAULT NULL,
  `vehicle_id` int DEFAULT NULL,
  `amount_residual` decimal(12,2) DEFAULT NULL COMMENT 'Odoo amount_residual — authoritative remaining balance'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `invoicesone` (
  `id` int NOT NULL AUTO_INCREMENT,
  `invoice_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `client_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `phone` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `account_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `car_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `model` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `vat_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `bid_amount` decimal(10,2) DEFAULT NULL,
  `year_of_manufacture` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `color` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `plate_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `chassis_number` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `total_insurance_paid` decimal(10,2) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `amount_before_discount` decimal(10,2) NOT NULL DEFAULT '0.00',
  `subtotal` decimal(10,2) NOT NULL DEFAULT '0.00',
  `taxes` decimal(10,2) NOT NULL DEFAULT '0.00',
  `discount` decimal(10,2) NOT NULL DEFAULT '0.00',
  `total` decimal(10,2) NOT NULL DEFAULT '0.00',
  `amount_due` decimal(10,2) NOT NULL DEFAULT '0.00',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=58 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `invoicesonepayment` (
  `id` int NOT NULL AUTO_INCREMENT,
  `invoice_id` int NOT NULL,
  `amount_paid` decimal(10,2) NOT NULL,
  `payment_date` date NOT NULL,
  PRIMARY KEY (`id`),
  KEY `invoice_id` (`invoice_id`),
  CONSTRAINT `invoicesonepayment_ibfk_1` FOREIGN KEY (`invoice_id`) REFERENCES `invoicesone` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `last2_20260805_bak` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2641 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `activity` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `ip` varchar(45) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `country` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `region` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `block_status` enum('allowed','blocked') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'allowed',
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `userss` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=182 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `management` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `role_key` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `phone` varchar(15) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `local_token_version` int NOT NULL DEFAULT '0',
  `updated_at` timestamp NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  KEY `idx_mgmt_role_key` (`role_key`),
  KEY `idx_active` (`is_active`)
) ENGINE=InnoDB AUTO_INCREMENT=77 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `management10` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `role` enum('owner','manager','deputy','supervisor','employee','data_entry','company','admin') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `management_audit_log` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `actor_id` int NOT NULL,
  `actor_username` varchar(100) NOT NULL,
  `action` varchar(50) NOT NULL,
  `target_id` int DEFAULT NULL,
  `target_username` varchar(100) DEFAULT NULL,
  `ip` varchar(45) DEFAULT NULL,
  `user_agent` varchar(255) DEFAULT NULL,
  `meta` json DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_actor` (`actor_id`),
  KEY `idx_target` (`target_id`),
  KEY `idx_action` (`action`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `management_card_overrides` (
  `id` int NOT NULL AUTO_INCREMENT,
  `management_id` int NOT NULL,
  `card_key` varchar(50) NOT NULL,
  `can_view` tinyint(1) NOT NULL DEFAULT '1',
  `can_edit` tinyint(1) DEFAULT NULL,
  `can_delete` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_admin_card` (`management_id`,`card_key`)
) ENGINE=InnoDB AUTO_INCREMENT=300 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `management_old_backup_20260607` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `role_key` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `phone` varchar(15) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `local_token_version` int NOT NULL DEFAULT '0',
  `updated_at` timestamp NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  KEY `idx_mgmt_role_key` (`role_key`),
  KEY `idx_active` (`is_active`)
) ENGINE=InnoDB AUTO_INCREMENT=39 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `merchants_auctions_sheet` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `id_user` int NOT NULL,
  `auction_id` int NOT NULL,
  `name_of_auction` varchar(255) DEFAULT NULL,
  `id_park` varchar(100) DEFAULT NULL,
  `car_name` varchar(255) DEFAULT NULL,
  `price_before_vat` decimal(10,2) NOT NULL DEFAULT '0.00',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_user_auction` (`id_user`,`auction_id`),
  KEY `idx_user` (`id_user`),
  KEY `idx_auction` (`auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1465 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `merchants_sheet` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `user_id` bigint unsigned NOT NULL,
  `auction_id` bigint unsigned NOT NULL,
  `name_of_auction` varchar(255) DEFAULT NULL,
  `id_park` varchar(100) DEFAULT NULL,
  `car_name` varchar(255) DEFAULT NULL,
  `price` decimal(12,2) NOT NULL DEFAULT '0.00',
  `price_with_vat` decimal(12,2) NOT NULL DEFAULT '0.00',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_auction` (`auction_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `messages` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `conv_id` int NOT NULL,
  `sender_type` enum('client','staff','system') NOT NULL,
  `staff_id` int DEFAULT NULL,
  `body` text,
  `attachment_path` varchar(255) DEFAULT NULL,
  `attachment_name` varchar(180) DEFAULT NULL,
  `is_read` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `conv_id` (`conv_id`),
  KEY `created_at` (`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `moyasar_payments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `reference` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `amount` decimal(10,2) DEFAULT NULL,
  `card_number` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `card_holder` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `card_brand` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=41 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `news_ticker` (
  `id` int NOT NULL AUTO_INCREMENT,
  `text_ar` varchar(255) NOT NULL,
  `text_en` varchar(255) DEFAULT NULL,
  `start_at` datetime DEFAULT NULL,
  `end_at` datetime DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_active_time` (`is_active`,`start_at`,`end_at`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `notifications` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `is_read` tinyint(1) DEFAULT '0',
  `type` enum('bid','win','payment','admin_message','admin_message','auctions_done','the_auction_is_about_to_end','send_money','warning','the_insurance_withdrawn','auto_bid','other') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `notifications_ibfk_1` (`user_id`),
  CONSTRAINT `notifications_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `userss` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=543946 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `notifications_payment` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `invoice_id` int NOT NULL,
  `message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `payment_details` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `due_date` datetime DEFAULT NULL,
  `notification_type` enum('unread','read') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `invoice_id` (`invoice_id`),
  CONSTRAINT `notifications_payment_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `userss` (`id`) ON DELETE CASCADE,
  CONSTRAINT `notifications_payment_ibfk_2` FOREIGN KEY (`invoice_id`) REFERENCES `invoices` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `odoo_customer_sync_pending` (
  `user_id` int unsigned NOT NULL,
  `attempts` int NOT NULL DEFAULT '0',
  `last_error` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `queued_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `odoo_inbox` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `endpoint` varchar(40) NOT NULL,
  `event` varchar(32) DEFAULT NULL,
  `odoo_customer_id` int DEFAULT NULL,
  `odoo_payment_id` varchar(64) DEFAULT NULL,
  `odoo_record_id` varchar(64) DEFAULT NULL,
  `payment_ref` varchar(128) DEFAULT NULL,
  `invoice_ref` varchar(64) DEFAULT NULL,
  `amount` decimal(14,2) DEFAULT NULL,
  `dedupe_key` varchar(190) DEFAULT NULL,
  `payload` mediumtext NOT NULL,
  `raw_body` mediumtext,
  `status` varchar(16) NOT NULL DEFAULT 'shadow',
  `resolved_user_id` int DEFAULT NULL,
  `legacy_http` smallint DEFAULT NULL,
  `legacy_result` varchar(64) DEFAULT NULL,
  `legacy_response` mediumtext,
  `legacy_at` datetime DEFAULT NULL,
  `received_at` datetime NOT NULL,
  `resolve_note` varchar(255) DEFAULT NULL,
  `last_try_at` datetime DEFAULT NULL,
  `try_count` smallint unsigned NOT NULL DEFAULT '0',
  `applied_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_status` (`status`),
  KEY `idx_customer` (`odoo_customer_id`),
  KEY `idx_dedupe` (`dedupe_key`),
  KEY `idx_received` (`received_at`),
  KEY `idx_legacy_http` (`legacy_http`)
) ENGINE=InnoDB AUTO_INCREMENT=5640 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `odoo_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `source` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `customer_id` int DEFAULT NULL,
  `payload` longtext CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci,
  `response` longtext CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_unicode_ci;

CREATE TABLE `odoo_payment_pushes` (
  `payment_reference` varchar(191) NOT NULL,
  `odoo_payment_id` varchar(64) NOT NULL,
  `amount` decimal(12,2) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`payment_reference`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `office_qr_tokens` (
  `id` int NOT NULL AUTO_INCREMENT,
  `token` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `expires_at` datetime NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `otp_events` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `phone` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ip` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `kind` enum('send','fail') COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_phone_kind_time` (`phone`,`kind`,`created_at`),
  KEY `idx_ip_time` (`ip`,`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=10749 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `packages` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `price` decimal(10,2) NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `type` enum('1','2','3') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `no_car` int DEFAULT '0',
  `active` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `paid_com` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_invoice` int NOT NULL,
  `amount` varchar(15) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `paid` int NOT NULL,
  `remain` int NOT NULL,
  `total` int NOT NULL,
  `status` enum('paid','Not_paid','part_paid') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `image` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `partial_payments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `car_id` int DEFAULT NULL,
  `amount` decimal(10,2) NOT NULL,
  `payment_method` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci NOT NULL,
  `full_name` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `transfer_date` date DEFAULT NULL,
  `receipt_image` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `status` enum('pending','aproverd','rejected') CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_user_payment_v2` (`user_id`),
  CONSTRAINT `fk_user_payment_v2` FOREIGN KEY (`user_id`) REFERENCES `userss` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_unicode_ci;

CREATE TABLE `partner_payments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `vehicle_id` int unsigned NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '0.00',
  `paid_at` date DEFAULT NULL,
  `note` varchar(200) DEFAULT NULL,
  `receipt_path` varchar(255) DEFAULT NULL,
  `batch_ref` varchar(64) DEFAULT NULL,
  `created_by` varchar(50) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_pp_vehicle` (`vehicle_id`),
  KEY `idx_pp_batch` (`batch_ref`)
) ENGINE=InnoDB AUTO_INCREMENT=85 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `payment_intents` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `gateway_payment_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `expected_amount` decimal(10,2) NOT NULL,
  `currency` char(3) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'SAR',
  `purpose` enum('subscription','insurance','invoice') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_gateway_payment_id` (`gateway_payment_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `payments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `payment_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `Mada` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '000201',
  `no_pch` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `user_id` int NOT NULL,
  `amount` int NOT NULL,
  `currency` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `odoo_payment_id` int DEFAULT NULL,
  `payment_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `state` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `fk_user_payment` FOREIGN KEY (`user_id`) REFERENCES `userss` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `payments_intents` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `customer_id` int NOT NULL,
  `payment_code` varchar(50) NOT NULL,
  `expected_amount` decimal(10,2) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `expires_at` datetime DEFAULT NULL,
  `moyasar_payment_id` varchar(100) DEFAULT NULL,
  `status` enum('created','paid','sent','failed','expired') NOT NULL DEFAULT 'created',
  `last_error` text,
  `intent_token` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_moyasar_intent` (`moyasar_payment_id`),
  UNIQUE KEY `uniq_intent_token` (`intent_token`),
  KEY `idx_user` (`user_id`),
  KEY `idx_customer` (`customer_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1097 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `payments_odoo` (
  `id` int NOT NULL AUTO_INCREMENT,
  `payment_id` int DEFAULT NULL,
  `customer_id` int DEFAULT NULL,
  `amount` decimal(10,2) DEFAULT NULL,
  `memo` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `payment_name` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `payment_code` varchar(20) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `status` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `invoice_id` int DEFAULT NULL,
  `payment_type` enum('partial','full') CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci NOT NULL DEFAULT 'partial',
  PRIMARY KEY (`id`),
  KEY `idx_customer_id` (`customer_id`),
  KEY `idx_invoice_id` (`invoice_id`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_payment_code` (`payment_code`),
  KEY `idx_payment_invoice` (`invoice_id`),
  KEY `idx_payment_customer` (`customer_id`),
  KEY `idx_payment_date` (`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=18999 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_unicode_ci;

CREATE TABLE `phantom_20260805_bak` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2680 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `plate_delivery_management` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `invoice_id` bigint unsigned NOT NULL,
  `invoice_number` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `car_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `car_plate` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `car_model` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `customer_id` bigint unsigned DEFAULT NULL,
  `user_id` bigint unsigned DEFAULT NULL,
  `customer_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `customer_phone` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `drawer_number` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sale_date` datetime DEFAULT NULL,
  `car_received_at` datetime DEFAULT NULL,
  `plates_received_at` datetime DEFAULT NULL,
  `ownership_transferred_at` datetime DEFAULT NULL,
  `transport_proof_file` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plate_delivery_status` enum('pending','car_received','plates_received','ownership_done') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'pending',
  `notes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_invoice_delivery` (`invoice_id`),
  KEY `idx_invoice_number` (`invoice_number`),
  KEY `idx_customer_phone` (`customer_phone`),
  KEY `idx_status` (`plate_delivery_status`),
  KEY `idx_plate_invoice_number` (`invoice_number`),
  KEY `idx_plate_phone` (`customer_phone`),
  KEY `idx_plate_status` (`plate_delivery_status`),
  KEY `idx_plate_sale_date` (`sale_date`),
  KEY `idx_plate_car_plate` (`car_plate`)
) ENGINE=InnoDB AUTO_INCREMENT=8192 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `products_stock` (
  `id` int NOT NULL AUTO_INCREMENT,
  `offer_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `avg_cost` decimal(12,2) DEFAULT NULL,
  `total_value` decimal(14,2) DEFAULT NULL,
  `qty_on_hand` int DEFAULT NULL,
  `svl_qty_layer` decimal(12,2) DEFAULT NULL,
  `qty_available` decimal(12,2) DEFAULT NULL,
  `incoming_qty` decimal(12,2) DEFAULT NULL,
  `outgoing_qty` decimal(12,2) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_offer_name` (`offer_name`),
  KEY `idx_qty` (`qty_on_hand`),
  KEY `idx_created` (`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=932 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `pull_20260803_bak` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2381 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `purchases` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `auction_id` int NOT NULL,
  `total_price` decimal(10,2) NOT NULL,
  `status` enum('تم الدفع','معلق','ملغي') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'معلق',
  `date` datetime DEFAULT CURRENT_TIMESTAMP,
  `payment_method` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `notes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `auction_id` (`auction_id`),
  CONSTRAINT `fk_purchase_auction` FOREIGN KEY (`auction_id`) REFERENCES `auctions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_purchase_user` FOREIGN KEY (`user_id`) REFERENCES `userss` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `qomah_20260805_bak` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2390 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `qr_codes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `qr_code` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `queue_counters` (
  `id` int NOT NULL AUTO_INCREMENT,
  `department_id` int NOT NULL,
  `employee_name` varchar(150) NOT NULL,
  `counter_name` varchar(50) NOT NULL,
  `is_online` tinyint(1) DEFAULT '1',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `department_id` (`department_id`),
  CONSTRAINT `queue_counters_ibfk_1` FOREIGN KEY (`department_id`) REFERENCES `queue_departments` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `queue_departments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name_ar` varchar(100) NOT NULL,
  `name_en` varchar(100) DEFAULT NULL,
  `prefix` varchar(10) NOT NULL,
  `avg_service_minutes` int DEFAULT '5',
  `is_active` tinyint(1) DEFAULT '1',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `queue_tickets` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint DEFAULT NULL,
  `user_mobile` varchar(30) DEFAULT NULL,
  `department_id` int NOT NULL,
  `ticket_number` varchar(30) NOT NULL,
  `source` enum('home','branch') DEFAULT 'home',
  `priority` enum('normal','vip') DEFAULT 'normal',
  `status` enum('waiting','called','in_service','done','cancelled','skipped') DEFAULT 'waiting',
  `qr_token` varchar(100) NOT NULL,
  `notes` text,
  `called_at` datetime DEFAULT NULL,
  `service_started_at` datetime DEFAULT NULL,
  `finished_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `user_mobile` (`user_mobile`),
  KEY `department_id` (`department_id`),
  KEY `status` (`status`),
  KEY `qr_token` (`qr_token`),
  CONSTRAINT `queue_tickets_ibfk_1` FOREIGN KEY (`department_id`) REFERENCES `queue_departments` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=222 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `recipient_id_images` (
  `id` int NOT NULL AUTO_INCREMENT,
  `exit_id` int DEFAULT NULL,
  `vehicle_id` int DEFAULT NULL,
  `recipient_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `recipient_id` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `recipient_phone` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `image_path` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `uploaded_by` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_exit` (`exit_id`),
  KEY `idx_rid` (`recipient_id`),
  KEY `idx_vehicle` (`vehicle_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2674 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `refund_requests` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(10,2) NOT NULL,
  `status` enum('pending','approved','rejected') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'pending',
  `processed` tinyint(1) DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `image` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `no_rin` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `refund_requests_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `userss` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `refunds_requests` (
  `id` int NOT NULL AUTO_INCREMENT,
  `customer_id` int NOT NULL,
  `amount` decimal(10,2) NOT NULL,
  `memo` text CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci,
  `payment_code` varchar(20) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `odoo_payment_id` int DEFAULT NULL,
  `status` enum('pending','approved','rejected') CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT 'pending',
  `payment_name` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `payment_state` varchar(20) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT 'draft',
  `iban_image` longtext CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci,
  `requested_at` datetime DEFAULT NULL,
  `iban_account` varchar(64) COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `deducted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_status` (`status`),
  KEY `idx_payment_state` (`payment_state`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_customer_id` (`customer_id`),
  KEY `idx_refunds_customer_id` (`customer_id`),
  KEY `idx_refund_customer` (`customer_id`),
  KEY `idx_refund_date` (`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=3393 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_unicode_ci;

CREATE TABLE `requests` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ip_address` varchar(45) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `restore_20260805_bak` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1658 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `role_card_permissions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `role_key` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `card_key` varchar(100) NOT NULL,
  `can_view` tinyint(1) NOT NULL DEFAULT '1',
  `can_edit` tinyint(1) NOT NULL DEFAULT '0',
  `can_delete` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_role_card` (`role_key`,`card_key`),
  UNIQUE KEY `uniq_role_card` (`role_key`,`card_key`),
  KEY `idx_role` (`role_key`),
  KEY `idx_card` (`card_key`),
  KEY `idx_rcp_card` (`card_key`),
  CONSTRAINT `fk_rcp_card` FOREIGN KEY (`card_key`) REFERENCES `cards` (`card_key`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=66012499 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `role_section_permissions` (
  `role_key` varchar(64) NOT NULL,
  `section_key` varchar(64) NOT NULL,
  `can_view` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`role_key`,`section_key`),
  KEY `fk_rsp_section` (`section_key`),
  CONSTRAINT `fk_rsp_section` FOREIGN KEY (`section_key`) REFERENCES `admin_sections` (`section_key`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `roles` (
  `id` int NOT NULL AUTO_INCREMENT,
  `role_key` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `role_name_ar` varchar(100) NOT NULL,
  `role_name_en` varchar(100) DEFAULT NULL,
  `name` varchar(50) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `role_key` (`role_key`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=7093 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `rubel_20260805_bak` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1658 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `settings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `site_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `site_description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `site_keywords` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `site_logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `site_status` tinyint(1) DEFAULT '1',
  `theme_mode` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'light',
  `bg_color` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '#ffffff',
  `text_color` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '#000000',
  `btn_color` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '#f6b427',
  `special_occasion_active` tinyint(1) DEFAULT '0',
  `default_auction_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'close',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `shares` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `auction_id` int NOT NULL,
  `shared_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `platform` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `auction_id` (`auction_id`),
  CONSTRAINT `shares_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `userss` (`id`) ON DELETE CASCADE,
  CONSTRAINT `shares_ibfk_2` FOREIGN KEY (`auction_id`) REFERENCES `auctions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `sms_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `phone` varchar(15) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `sent_at` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=74876 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `social_media` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `link` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `text` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `staff` (
  `id` int NOT NULL AUTO_INCREMENT,
  `dept_id` int NOT NULL,
  `name` varchar(100) NOT NULL,
  `username` varchar(100) DEFAULT NULL,
  `avatar_url` varchar(255) DEFAULT NULL,
  `wa_number` varchar(20) DEFAULT NULL,
  `livechat_url` varchar(255) DEFAULT NULL,
  `email` varchar(150) DEFAULT NULL,
  `is_online` tinyint(1) NOT NULL DEFAULT '0',
  `last_seen` timestamp NULL DEFAULT NULL,
  `note` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `dept_id` (`dept_id`),
  CONSTRAINT `staff_ibfk_1` FOREIGN KEY (`dept_id`) REFERENCES `departments` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `statistics` (
  `id` int NOT NULL AUTO_INCREMENT,
  `category` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `count` int NOT NULL,
  `color` varchar(7) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '#000000',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `support_chat_sessions` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `user_id` bigint unsigned NOT NULL,
  `department` enum('support','finance','accounts') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'support',
  `status` enum('open','closed') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'open',
  `created_at` datetime NOT NULL,
  `closed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_dept` (`department`),
  KEY `idx_status` (`status`),
  KEY `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `support_messages` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `phone` varchar(20) NOT NULL,
  `email` varchar(150) NOT NULL,
  `message` text NOT NULL,
  `ip` varchar(45) DEFAULT NULL,
  `user_agent` varchar(255) DEFAULT NULL,
  `status` enum('new','in_progress','closed') NOT NULL DEFAULT 'new',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=221 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `support_replies` (
  `id` int NOT NULL AUTO_INCREMENT,
  `message_id` int NOT NULL,
  `admin_username` varchar(100) NOT NULL,
  `subject` varchar(200) NOT NULL,
  `body` text NOT NULL,
  `sent_via` enum('email','internal') NOT NULL DEFAULT 'email',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `message_id` (`message_id`),
  CONSTRAINT `support_replies_ibfk_1` FOREIGN KEY (`message_id`) REFERENCES `support_messages` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `support_tickets` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `user_id` bigint unsigned NOT NULL,
  `user_name` varchar(190) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `user_phone` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `department` enum('support','finance','accounts') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'support',
  `priority` enum('low','normal','high') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'normal',
  `subject` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` enum('open','pending','answered','closed') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'open',
  `admin_reply` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `assigned_admin` varchar(190) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_dept` (`department`),
  KEY `idx_status` (`status`),
  KEY `idx_created` (`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=546 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `themes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `code` varchar(50) NOT NULL,
  `bg_color` varchar(20) NOT NULL,
  `text_color` varchar(20) NOT NULL,
  `btn_color` varchar(20) NOT NULL,
  `is_active` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `themes1` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '0',
  `brand_color` varchar(9) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '#4f46e5',
  `chip_color` varchar(9) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '#eef2ff',
  `card_color` varchar(9) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '#ffffff',
  `body_bg` varchar(9) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '#f7f7fb',
  `text_color` varchar(9) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '#111111',
  `radius_px` int NOT NULL DEFAULT '14',
  `shadow_lvl` tinyint NOT NULL DEFAULT '2',
  `img_h` int NOT NULL DEFAULT '120',
  `ticker_speed` int NOT NULL DEFAULT '35',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `info_color` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `transfer_requests` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `request_type` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'ownership_transfer',
  `user_id` int unsigned NOT NULL,
  `car_id` int unsigned NOT NULL DEFAULT '0',
  `invoice_id` int unsigned NOT NULL DEFAULT '0',
  `payment_method` enum('bank','branch') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `amount` decimal(10,2) NOT NULL DEFAULT '0.00',
  `status` enum('pending','processing','completed','rejected','cancelled') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `progress_step` enum('form','tanazul','owner_id','lost_letter','renewed') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'form',
  `status_note` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `notes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `new_owner_id_path` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `new_owner_license_path` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bank_account_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bank_iban` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bank_transfer_date` date DEFAULT NULL,
  `bank_sender_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bank_transfer_image_path` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  `amount_approved` decimal(12,2) DEFAULT NULL,
  `odoo_payment_id` varchar(191) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `receipt_path` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `admin_note` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_car_id` (`car_id`),
  KEY `idx_invoice_id` (`invoice_id`)
) ENGINE=InnoDB AUTO_INCREMENT=233 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `translation_options` (
  `id` int NOT NULL AUTO_INCREMENT,
  `translation_id` int NOT NULL,
  `option_key` varchar(100) NOT NULL,
  `option_value_arabic` varchar(255) DEFAULT NULL,
  `option_value_english` varchar(255) DEFAULT NULL,
  `option_value_urdu` varchar(255) DEFAULT NULL,
  `option_value_hindi` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_translation_option` (`translation_id`,`option_key`),
  KEY `idx_translation` (`translation_id`),
  CONSTRAINT `fk_translation_options_parent` FOREIGN KEY (`translation_id`) REFERENCES `auction_translations` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1027 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `turn_bookings` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `phone` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `department` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `location` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `turn_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_turn_bookings_user_id` (`user_id`),
  KEY `idx_turn_bookings_status` (`status`),
  KEY `idx_turn_bookings_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `undo_11603_bak_bids` (
  `id` int NOT NULL AUTO_INCREMENT,
  `auction_id` int NOT NULL,
  `user_id` int NOT NULL,
  `amount` int NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `paid_amount` decimal(10,2) DEFAULT '0.00',
  `is_auto` tinyint(1) DEFAULT '0',
  `offer_status` enum('pending','accepted','rejected') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'pending',
  `sms_sent` tinyint(1) DEFAULT '0',
  `amount_with_vat` decimal(10,2) DEFAULT NULL,
  `auction_name` int DEFAULT NULL,
  `status` enum('active','not_active','deleted') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `vehicle_id` int DEFAULT NULL,
  `rank` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `bids_ibfk_1` (`auction_id`),
  KEY `bids_ibfk_2` (`user_id`),
  KEY `idx_bids_vehicle` (`vehicle_id`),
  KEY `idx_bids_vehicle_rank` (`vehicle_id`,`rank`),
  KEY `idx_bids_vehicle_id` (`vehicle_id`),
  KEY `idx_bids_user_id` (`user_id`),
  KEY `idx_bids_vehicle_status_amount` (`vehicle_id`,`status`,`amount`),
  KEY `idx_bids_auction_status_amount` (`auction_id`,`status`,`amount`)
) ENGINE=InnoDB AUTO_INCREMENT=104521 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `undo_11603_bak_vehicles` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `auction_id` int DEFAULT NULL,
  `campaign_id` int unsigned DEFAULT NULL,
  `lot_number` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `vehicle_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `make` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `model` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `year` int DEFAULT NULL,
  `starting_price` decimal(12,2) NOT NULL DEFAULT '0.00',
  `vehicle_condition` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Intact',
  `condition_notes` text COLLATE utf8mb4_unicode_ci,
  `vehicle_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `settings_override` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `override_settings` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT NULL,
  `vehicle_brand` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `year_of_manufacture` int DEFAULT NULL,
  `mileage` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `the_color` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Plate_number` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plate_type` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chassis_number` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `insurance_company` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `overview` text COLLATE utf8mb4_unicode_ci,
  `mvpi_status` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `auto_bid` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bidamount` decimal(12,2) DEFAULT NULL,
  `activation_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inspection_days` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `time_periods` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `preview_site` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `the_doors` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `the_weight` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `input_time` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inspection_report_media` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `winner_user_id` int DEFAULT NULL,
  `final_price` decimal(12,2) DEFAULT NULL,
  `winner_paid_at` datetime DEFAULT NULL,
  `payment_method` varchar(60) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transaction_ref` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `receipt_image_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `winning_bid_id` int DEFAULT NULL,
  `awarded_at` datetime DEFAULT NULL,
  `approval_status` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'pending=awaiting admin approval, approved=winner confirmed, rejected=admin rejected',
  `display_image` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fuel_type` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `runs_status` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `key_status` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_auction_vehicles_auction_id` (`auction_id`),
  KEY `idx_auction_vehicles_status` (`status`),
  CONSTRAINT `undo_11603_bak_vehicles_chk_1` CHECK (json_valid(`vehicle_data`)),
  CONSTRAINT `undo_11603_bak_vehicles_chk_2` CHECK (json_valid(`settings_override`)),
  CONSTRAINT `undo_11603_bak_vehicles_chk_3` CHECK (json_valid(`override_settings`))
) ENGINE=InnoDB AUTO_INCREMENT=11604 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `user_auctions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `auction_id` int NOT NULL,
  `status` enum('active','inactive') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'active',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `auction_id` (`auction_id`),
  CONSTRAINT `user_auctions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `userss` (`id`),
  CONSTRAINT `user_auctions_ibfk_2` FOREIGN KEY (`auction_id`) REFERENCES `auctions` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `user_card_permissions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `card_key` varchar(100) NOT NULL,
  `allowed` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_user_card` (`user_id`,`card_key`),
  KEY `idx_user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `user_tokens` (
  `id` int NOT NULL AUTO_INCREMENT,
  `token` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `userss` (
  `id` int NOT NULL AUTO_INCREMENT,
  `phone` varchar(15) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `verification_code` varchar(4) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `failed_attempts` int NOT NULL DEFAULT '0',
  `last_attempt_time` datetime DEFAULT NULL,
  `block_status` enum('allowed','blocked') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'allowed',
  `code_expiry` datetime DEFAULT NULL,
  `identity_type` enum('id','residency') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `identity_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `type_of_account` enum('personal','company') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `tax_image` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `birth_date` date DEFAULT NULL,
  `arabic_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `cr_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `english_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `gender` enum('male','female') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `identity_image` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `total_insurance_paid` decimal(10,2) NOT NULL DEFAULT '0.00',
  `purchases_balance` decimal(12,2) NOT NULL DEFAULT '0.00',
  `wallet` decimal(12,2) NOT NULL DEFAULT '0.00',
  `id_customer` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `active_auctions_count` int DEFAULT '0',
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `last_resend_time` datetime DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `iban_account` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `commerce_image` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `company_image` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `national_address_image` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `passport_image` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `country` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `plot_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `blocked_until` datetime DEFAULT NULL,
  `id_package` int DEFAULT '9',
  `address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `zip` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `building_no` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `vat_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `street` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `district` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `state` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `profile_image` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `city` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `player_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `additional_no` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `fcm_token` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `session_token` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `mobile_verified` tinyint(1) DEFAULT '0',
  `remember_token_hash` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `remember_token_expires_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `phone` (`phone`),
  UNIQUE KEY `phone_2` (`phone`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `email_2` (`email`),
  UNIQUE KEY `identity_number_2` (`identity_number`),
  UNIQUE KEY `identity_number_3` (`identity_number`),
  KEY `fk_userss_package` (`id_package`),
  KEY `idx_userss_id_customer` (`id_customer`),
  KEY `idx_phone` (`phone`),
  KEY `idx_arabic_name` (`arabic_name`),
  KEY `idx_block_status` (`block_status`),
  KEY `idx_type_of_account` (`type_of_account`),
  KEY `idx_name_phone` (`arabic_name`,`phone`),
  KEY `idx_users_customer` (`id_customer`),
  KEY `idx_userss_phone` (`phone`),
  KEY `idx_userss_session_token` (`session_token`),
  CONSTRAINT `fk_userss_package` FOREIGN KEY (`id_package`) REFERENCES `packages` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=44439 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `userss_bak_20260820_154444_jawad` (
  `id` int NOT NULL DEFAULT '0',
  `phone` varchar(15) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `verification_code` varchar(4) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `failed_attempts` int NOT NULL DEFAULT '0',
  `last_attempt_time` datetime DEFAULT NULL,
  `block_status` enum('allowed','blocked') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'allowed',
  `code_expiry` datetime DEFAULT NULL,
  `identity_type` enum('id','residency') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `identity_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `type_of_account` enum('personal','company') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `tax_image` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `birth_date` date DEFAULT NULL,
  `arabic_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `cr_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `english_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `gender` enum('male','female') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `identity_image` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `total_insurance_paid` decimal(10,2) NOT NULL DEFAULT '0.00',
  `purchases_balance` decimal(12,2) NOT NULL DEFAULT '0.00',
  `wallet` decimal(12,2) NOT NULL DEFAULT '0.00',
  `id_customer` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `active_auctions_count` int DEFAULT '0',
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `last_resend_time` datetime DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `iban_account` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `commerce_image` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `company_image` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `national_address_image` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `passport_image` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `country` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `plot_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `blocked_until` datetime DEFAULT NULL,
  `id_package` int DEFAULT '9',
  `address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `zip` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `building_no` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `vat_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `street` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `district` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `state` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `profile_image` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `city` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `player_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `additional_no` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `fcm_token` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `session_token` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `mobile_verified` tinyint(1) DEFAULT '0',
  `remember_token_hash` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `remember_token_expires_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `vehicle_exits` (
  `id` int NOT NULL AUTO_INCREMENT,
  `vehicle_id` int NOT NULL,
  `auction_id` int DEFAULT NULL,
  `invoice_id` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `buyer_user_id` int DEFAULT NULL,
  `recipient_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `recipient_id` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `recipient_phone` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `recipient_id_image` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exit_type` enum('after_transfer','without_transfer','repair_inspection') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exit_reason` enum('no_plates_no_inspection','no_plates_ban','no_problem') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transfer_status` enum('pending','transferred','without_transfer') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `barcode` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `declaration_file` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transfer_proof_file` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stage` enum('created','sent_to_gate','exited','under_transfer','archived') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'created',
  `warehouse_exit_at` datetime DEFAULT NULL,
  `transfer_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  `created_by` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `manager_alerted_at` datetime DEFAULT NULL,
  `owner_alerted_at` datetime DEFAULT NULL,
  `declaration_date` date DEFAULT NULL,
  `ban_lifted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_barcode` (`barcode`),
  KEY `idx_vehicle` (`vehicle_id`),
  KEY `idx_stage` (`stage`),
  KEY `idx_transfer` (`transfer_status`),
  KEY `idx_exit_at` (`warehouse_exit_at`)
) ENGINE=InnoDB AUTO_INCREMENT=2653 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `vehicle_exits_bak_20260716_145551` (
  `id` int NOT NULL AUTO_INCREMENT,
  `vehicle_id` int NOT NULL,
  `auction_id` int DEFAULT NULL,
  `invoice_id` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `buyer_user_id` int DEFAULT NULL,
  `recipient_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `recipient_id` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `recipient_phone` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `recipient_id_image` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exit_type` enum('after_transfer','without_transfer','repair_inspection') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exit_reason` enum('no_plates_no_inspection','no_plates_ban','no_problem') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transfer_status` enum('pending','transferred','without_transfer') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `barcode` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `declaration_file` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transfer_proof_file` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stage` enum('created','sent_to_gate','exited','under_transfer','archived') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'created',
  `warehouse_exit_at` datetime DEFAULT NULL,
  `transfer_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  `created_by` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `manager_alerted_at` datetime DEFAULT NULL,
  `owner_alerted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_barcode` (`barcode`),
  KEY `idx_vehicle` (`vehicle_id`),
  KEY `idx_stage` (`stage`),
  KEY `idx_transfer` (`transfer_status`),
  KEY `idx_exit_at` (`warehouse_exit_at`)
) ENGINE=InnoDB AUTO_INCREMENT=467 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `vehicle_receipt` (
  `id` int NOT NULL AUTO_INCREMENT,
  `date_received` datetime DEFAULT NULL,
  `recipient_name` varchar(255) DEFAULT NULL,
  `image_path` varchar(255) DEFAULT NULL,
  `id_number` varchar(100) DEFAULT NULL,
  `vehicle_type` varchar(100) DEFAULT NULL,
  `model` varchar(100) DEFAULT NULL,
  `color` varchar(100) DEFAULT NULL,
  `plate_number` varchar(100) DEFAULT NULL,
  `chassis_number` varchar(100) DEFAULT NULL,
  `phone_number` varchar(100) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `vehicles` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `color` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `mileage` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `year` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `price` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `waiver_requests` (
  `id` int NOT NULL AUTO_INCREMENT,
  `date_received` date NOT NULL,
  `recipient_name` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci NOT NULL,
  `owner_name` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci NOT NULL,
  `image_path` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci NOT NULL,
  `id_number` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci NOT NULL,
  `vehicle_type` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci NOT NULL,
  `model` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci NOT NULL,
  `color` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `plate_number` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci NOT NULL,
  `chassis_number` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `phone_number` varchar(20) CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `request_type` varchar(30) COLLATE utf8mb3_unicode_ci DEFAULT 'waiver',
  `status` varchar(30) COLLATE utf8mb3_unicode_ci NOT NULL DEFAULT 'pending',
  `status_note` varchar(255) COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  `progress_step` varchar(60) COLLATE utf8mb3_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_unicode_ci;

CREATE TABLE `wallet_health_findings` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `code` varchar(32) NOT NULL,
  `subject` varchar(48) NOT NULL,
  `severity` varchar(10) NOT NULL,
  `title` varchar(200) NOT NULL,
  `detail` varchar(500) DEFAULT NULL,
  `amount` decimal(14,2) NOT NULL DEFAULT '0.00',
  `status` varchar(10) NOT NULL DEFAULT 'open',
  `acknowledged_by` int DEFAULT NULL,
  `acknowledged_at` datetime DEFAULT NULL,
  `first_seen_at` datetime NOT NULL,
  `last_seen_at` datetime NOT NULL,
  `resolved_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_finding` (`code`,`subject`),
  KEY `idx_status` (`status`),
  KEY `idx_severity` (`severity`),
  KEY `idx_last_seen` (`last_seen_at`)
) ENGINE=InnoDB AUTO_INCREMENT=3450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `wallet_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(10,2) NOT NULL,
  `added_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `wallet_logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `userss` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `wallet_transactions` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `category` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `amount` decimal(12,2) NOT NULL,
  `odoo_reference` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transfer_request_id` int unsigned DEFAULT NULL,
  `note` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_odoo_reference` (`odoo_reference`),
  KEY `idx_wt_user` (`user_id`),
  KEY `idx_wt_type` (`type`),
  KEY `idx_wt_category` (`category`),
  KEY `idx_wt_odoo_payment` (`odoo_payment_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5531 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `webhook_failures` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `endpoint` varchar(191) NOT NULL,
  `method` varchar(10) DEFAULT NULL,
  `http_status` smallint unsigned NOT NULL,
  `message` varchar(191) DEFAULT NULL,
  `detail` text,
  `request_body` mediumtext,
  `response_body` mediumtext,
  `remote_ip` varchar(45) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_created` (`created_at`),
  KEY `idx_status` (`http_status`),
  KEY `idx_endpoint` (`endpoint`)
) ENGINE=InnoDB AUTO_INCREMENT=48 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `zaar_20260805_bak` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free',
  `odoo_payment_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `linked_auction_id` int DEFAULT NULL,
  `linked_invoice_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `held_at` datetime DEFAULT NULL,
  `locked_at` datetime DEFAULT NULL,
  `refunded_at` datetime DEFAULT NULL,
  `confiscated_at` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_status` (`user_id`,`status`),
  KEY `idx_odoo_payment` (`odoo_payment_id`),
  KEY `idx_auction` (`linked_auction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2666 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
