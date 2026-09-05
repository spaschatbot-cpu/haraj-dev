-- بيانات اختبار مُصطنَعة لبنية v1 — ثلاثة صفوف في كل جدول.
--
-- **لا صفَّ حقيقياً واحداً هنا.** كل اسمٍ ورقمِ جوالٍ ورقمِ هويّةٍ ومبلغ
-- مُختلَق، ومُختلَقٌ ليبدو مُختلقاً: تجهيزةٌ يظنّها قارئٌ بياناتٍ حقيقية
-- تجهيزةٌ يعاملها أحدهم يوماً على أنها كذلك. ونسخةُ الإنتاج نفسها لا
-- تدخل المستودع (المادة 5-3، وانظر رأس `v1-schema.sql`).
--
-- مولَّدٌ حتمياً من `v1-schema.sql`: البنية نفسها تعطي الملفّ نفسه، فما
-- يظهر في `git diff` هو ما تغيّر في البنية لا ترتيبٌ عشوائي.
--
-- المعرّفات 1 و2 و3 في كل جدول، وكل مفتاح أجنبي يشير إلى الصفّ المقابل
-- في أبيه — فالربط يعمل، والجداول مرتَّبة آباءً قبل أبناء ليمرّ التحميل
-- بأمر واحد:
--
--     mysql -u <user> hara_clone_v1_test < v1-schema.sql
--     mysql -u <user> hara_clone_v1_test < v1-seed.sql

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS=0;

INSERT INTO `abubakr_20260805_bak_bids` (`id`, `auction_id`, `user_id`, `amount`, `created_at`, `paid_amount`, `is_auto`, `offer_status`, `sms_sent`, `amount_with_vat`, `auction_name`, `status`, `vehicle_id`, `rank`) VALUES
(1, 1, 1, 1, '2026-01-01 09:00:00', 1000.00, 0, 'pending', 0, 1000.00, 1, 'active', 1, 1),
(2, 2, 2, 2, '2026-01-02 09:00:00', 2000.00, 0, 'pending', 0, 2000.00, 2, 'active', 2, 2),
(3, 3, 3, 3, '2026-01-03 09:00:00', 3000.00, 0, 'pending', 0, 3000.00, 3, 'active', 3, 3);

INSERT INTO `abubakr_20260805_bak_deposits` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'abubakr_20260805_bak_deposits-odoo_payment_id-1', 1, 'abubakr_20260805_bak_deposits-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (abubakr_20260805_bak_deposits)'),
(2, 2, 2000.00, 'test', 'abubakr_20260805_bak_deposits-odoo_payment_id-2', 2, 'abubakr_20260805_bak_deposits-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (abubakr_20260805_bak_deposits)'),
(3, 3, 3000.00, 'test', 'abubakr_20260805_bak_deposits-odoo_payment_id-3', 3, 'abubakr_20260805_bak_deposits-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (abubakr_20260805_bak_deposits)');

INSERT INTO `account_page_settings` (`setting_key`, `setting_value`, `updated_at`) VALUES
('account_page_settings-setting_key-1', 'account_page_settings-setting_value-1', '2026-01-01 09:00:00'),
('account_page_settings-setting_key-2', 'account_page_settings-setting_value-2', '2026-01-02 09:00:00'),
('account_page_settings-setting_key-3', 'account_page_settings-setting_value-3', '2026-01-03 09:00:00');

INSERT INTO `admin_login_attempts` (`id`, `ip`, `username`, `attempts`, `locked_until`, `last_attempt_at`) VALUES
(1, 'admin_login_attempts-ip-1', 'تجريبي 1 — admin_login_attempts', 1, '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 'admin_login_attempts-ip-2', 'تجريبي 2 — admin_login_attempts', 2, '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 'admin_login_attempts-ip-3', 'تجريبي 3 — admin_login_attempts', 3, '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `admin_notifications` (`id`, `type`, `title`, `body`, `ref_table`, `ref_id`, `is_read`, `read_at`, `created_at`) VALUES
(1, 'test', 'تجريبي 1 — admin_notifications', 'admin_notifications-body-1', 'admin_notifications-ref_table-1', 1, 0, '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 'test', 'تجريبي 2 — admin_notifications', 'admin_notifications-body-2', 'admin_notifications-ref_table-2', 2, 0, '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 'test', 'تجريبي 3 — admin_notifications', 'admin_notifications-body-3', 'admin_notifications-ref_table-3', 3, 0, '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `admin_sections` (`id`, `section_key`, `name_ar`, `name_en`, `href`, `description_ar`, `description_en`, `sort_order`, `is_active`, `created_at`) VALUES
(1, 'admin_sections-section_key-1', 'تجريبي 1 — admin_sections', 'تجريبي 1 — admin_sections', 'admin_sections-href-1', 'admin_sections-description_ar-1', 'admin_sections-description_en-1', 1, 0, '2026-01-01 09:00:00'),
(2, 'admin_sections-section_key-2', 'تجريبي 2 — admin_sections', 'تجريبي 2 — admin_sections', 'admin_sections-href-2', 'admin_sections-description_ar-2', 'admin_sections-description_en-2', 2, 0, '2026-01-02 09:00:00'),
(3, 'admin_sections-section_key-3', 'تجريبي 3 — admin_sections', 'تجريبي 3 — admin_sections', 'admin_sections-href-3', 'admin_sections-description_ar-3', 'admin_sections-description_en-3', 3, 0, '2026-01-03 09:00:00');

INSERT INTO `aftersales_hidden_auctions` (`auction_id`, `hidden_by`, `hidden_at`) VALUES
(1, 'aftersales_hidden_auctions-hidden_by-1', '2026-01-01 09:00:00'),
(2, 'aftersales_hidden_auctions-hidden_by-2', '2026-01-02 09:00:00'),
(3, 'aftersales_hidden_auctions-hidden_by-3', '2026-01-03 09:00:00');

INSERT INTO `amount` (`id`, `insurance_per_auction`) VALUES
(1, 1),
(2, 2),
(3, 3);

INSERT INTO `employees` (`id`, `name`, `phone`, `email`, `password_hash`, `role`, `status`, `created_at`, `api_token_hash`, `api_token_expires`) VALUES
(1, 'تجريبي 1 — employees', '966500000001', 'test1@example.invalid', 'NOT-A-REAL-SECRET-1', 'admin', 0, '2026-01-01 09:00:00', 'NOT-A-REAL-SECRET-1', '2026-01-01 09:00:00'),
(2, 'تجريبي 2 — employees', '966500000002', 'test2@example.invalid', 'NOT-A-REAL-SECRET-2', 'admin', 0, '2026-01-02 09:00:00', 'NOT-A-REAL-SECRET-2', '2026-01-02 09:00:00'),
(3, 'تجريبي 3 — employees', '966500000003', 'test3@example.invalid', 'NOT-A-REAL-SECRET-3', 'admin', 0, '2026-01-03 09:00:00', 'NOT-A-REAL-SECRET-3', '2026-01-03 09:00:00');

INSERT INTO `api_tokens` (`id`, `employee_id`, `token`, `expires_at`, `created_at`, `last_used_at`) VALUES
(1, 1, 'NOT-A-REAL-SECRET-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 2, 'NOT-A-REAL-SECRET-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 3, 'NOT-A-REAL-SECRET-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `app_meta` (`meta_key`, `meta_value`, `updated_at`) VALUES
('app_meta-meta_key-1', 'app_meta-meta_value-1', '2026-01-01 09:00:00'),
('app_meta-meta_key-2', 'app_meta-meta_value-2', '2026-01-02 09:00:00'),
('app_meta-meta_key-3', 'app_meta-meta_value-3', '2026-01-03 09:00:00');

INSERT INTO `app_settings` (`skey`, `svalue`, `updated_at`) VALUES
('app_settings-skey-1', 'app_settings-svalue-1', '2026-01-01 09:00:00'),
('app_settings-skey-2', 'app_settings-svalue-2', '2026-01-02 09:00:00'),
('app_settings-skey-3', 'app_settings-svalue-3', '2026-01-03 09:00:00');

INSERT INTO `attendance` (`id`, `employee_id`, `date`, `checkin_time`, `checkout_time`, `source`, `qr_token`, `synced`, `created_at`, `updated_at`) VALUES
(1, 1, '2026-01-01', '09:00:00', '09:00:00', 'mobile', 'NOT-A-REAL-SECRET-1', 0, '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 2, '2026-01-02', '09:00:00', '09:00:00', 'mobile', 'NOT-A-REAL-SECRET-2', 0, '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 3, '2026-01-03', '09:00:00', '09:00:00', 'mobile', 'NOT-A-REAL-SECRET-3', 0, '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `auction_campaigns` (`id`, `title`, `start_time`, `end_time`, `sms_reminder_time`, `general_settings`, `status`, `created_at`, `updated_at`) VALUES
(1, 'تجريبي 1 — auction_campaigns', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'auction_campaigns-general_settings-1', 'test', '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 'تجريبي 2 — auction_campaigns', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'auction_campaigns-general_settings-2', 'test', '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 'تجريبي 3 — auction_campaigns', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'auction_campaigns-general_settings-3', 'test', '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `auction_name` (`id`, `au_name`, `start`, `end`, `create_at`) VALUES
(1, 'تجريبي 1 — auction_name', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 'تجريبي 2 — auction_name', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 'تجريبي 3 — auction_name', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `auction_park_logs` (`id`, `auction_id`, `detail_id`, `old_id_park`, `new_id_park`, `admin_username`, `admin_role`, `ip_address`, `user_agent`, `created_at`) VALUES
(1, 1, 1, 'auction_park_logs-old_id_park-1', 'auction_park_logs-new_id_park-1', 'تجريبي 1 — auction_park_logs', 'auction_park_logs-admin_role-1', 'auction_park_logs-ip_address-1', 'auction_park_logs-user_agent-1', '2026-01-01 09:00:00'),
(2, 2, 2, 'auction_park_logs-old_id_park-2', 'auction_park_logs-new_id_park-2', 'تجريبي 2 — auction_park_logs', 'auction_park_logs-admin_role-2', 'auction_park_logs-ip_address-2', 'auction_park_logs-user_agent-2', '2026-01-02 09:00:00'),
(3, 3, 3, 'auction_park_logs-old_id_park-3', 'auction_park_logs-new_id_park-3', 'تجريبي 3 — auction_park_logs', 'auction_park_logs-admin_role-3', 'auction_park_logs-ip_address-3', 'auction_park_logs-user_agent-3', '2026-01-03 09:00:00');

INSERT INTO `auction_translations` (`id`, `key_name`, `value_arabic`, `value_english`, `value_urdu`, `value_hindi`, `has_options`, `created_at`) VALUES
(1, 'تجريبي 1 — auction_translations', 'auction_translations-value_arabic-1', 'auction_translations-value_english-1', 'auction_translations-value_urdu-1', 'auction_translations-value_hindi-1', 0, '2026-01-01 09:00:00'),
(2, 'تجريبي 2 — auction_translations', 'auction_translations-value_arabic-2', 'auction_translations-value_english-2', 'auction_translations-value_urdu-2', 'auction_translations-value_hindi-2', 0, '2026-01-02 09:00:00'),
(3, 'تجريبي 3 — auction_translations', 'auction_translations-value_arabic-3', 'auction_translations-value_english-3', 'auction_translations-value_urdu-3', 'auction_translations-value_hindi-3', 0, '2026-01-03 09:00:00');

INSERT INTO `auction_translation_options` (`id`, `translation_id`, `option_key`, `value_arabic`, `value_english`, `value_urdu`, `value_hindi`, `sort_order`, `created_at`) VALUES
(1, 1, 'auction_translation_options-option_key-1', 'auction_translation_options-value_arabic-1', 'auction_translation_options-value_english-1', 'auction_translation_options-value_urdu-1', 'auction_translation_options-value_hindi-1', 1, '2026-01-01 09:00:00'),
(2, 2, 'auction_translation_options-option_key-2', 'auction_translation_options-value_arabic-2', 'auction_translation_options-value_english-2', 'auction_translation_options-value_urdu-2', 'auction_translation_options-value_hindi-2', 2, '2026-01-02 09:00:00'),
(3, 3, 'auction_translation_options-option_key-3', 'auction_translation_options-value_arabic-3', 'auction_translation_options-value_english-3', 'auction_translation_options-value_urdu-3', 'auction_translation_options-value_hindi-3', 3, '2026-01-03 09:00:00');

INSERT INTO `auctions` (`id`, `name_of_auction`, `car_name`, `image`, `id_park`, `mileage`, `starting_price`, `increment`, `start_time`, `end_time`, `status`, `offer_status`, `type_auctions`, `vat_type`, `fees`, `share_count`, `created_at`, `sms_reminder_time`, `is_mega_auction`, `insurance_amount`) VALUES
(1, 'تجريبي 1 — auctions', 'تجريبي 1 — auctions', 'fixtures/auctions/1.jpg', 'auctions-id_park-1', 'auctions-mileage-1', 1000.00, 1000.00, '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'not_active', 'test', 'test', '300000000000001', 1000.00, 1, '2026-01-01 09:00:00', '2026-01-01 09:00:00', 0, 1000.00),
(2, 'تجريبي 2 — auctions', 'تجريبي 2 — auctions', 'fixtures/auctions/2.jpg', 'auctions-id_park-2', 'auctions-mileage-2', 2000.00, 2000.00, '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'not_active', 'test', 'test', '300000000000002', 2000.00, 2, '2026-01-02 09:00:00', '2026-01-02 09:00:00', 0, 2000.00),
(3, 'تجريبي 3 — auctions', 'تجريبي 3 — auctions', 'fixtures/auctions/3.jpg', 'auctions-id_park-3', 'auctions-mileage-3', 3000.00, 3000.00, '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'not_active', 'test', 'test', '300000000000003', 3000.00, 3, '2026-01-03 09:00:00', '2026-01-03 09:00:00', 0, 3000.00);

INSERT INTO `auction_vehicles` (`id`, `auction_id`, `campaign_id`, `lot_number`, `vehicle_name`, `make`, `model`, `year`, `starting_price`, `vehicle_condition`, `condition_notes`, `vehicle_data`, `settings_override`, `override_settings`, `status`, `created_at`, `updated_at`, `vehicle_brand`, `year_of_manufacture`, `mileage`, `the_color`, `Plate_number`, `plate_type`, `chassis_number`, `insurance_company`, `overview`, `mvpi_status`, `auto_bid`, `bidamount`, `activation_status`, `inspection_days`, `time_periods`, `preview_site`, `the_doors`, `the_weight`, `input_time`, `inspection_report_media`, `winner_user_id`, `final_price`, `winner_paid_at`, `payment_method`, `transaction_ref`, `receipt_image_path`, `winning_bid_id`, `awarded_at`, `approval_status`, `display_image`, `fuel_type`, `runs_status`, `key_status`, `is_marketing`, `partner_decision`, `partner_decision_bid_id`, `partner_decided_at`, `partner_decided_by`, `claim_number`) VALUES
(1, 1, 1, 'auction_vehicles-lot_number-1', 'تجريبي 1 — auction_vehicles', 'auction_vehicles-make-1', 'auction_vehicles-model-1', 1, 1000.00, 'auction_vehicles-vehicle_condition-1', 'بيانات اختبار مُصطنَعة (auction_vehicles)', 'auction_vehicles-vehicle_data-1', 'auction_vehicles-settings_override-1', 'auction_vehicles-override_settings-1', 'test', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'auction_vehicles-vehicle_brand-1', 1, 'auction_vehicles-mileage-1', 'auction_vehicles-the_color-1', 'auction_vehicles-Plate_number-1', 'test', 'auction_vehicles-chassis_number-1', 'auction_vehicles-insurance_company-1', 'auction_vehicles-overview-1', 'test', 'auction_vehicles-auto_bid-1', 1000.00, '300000000000001', 'auction_vehicles-inspection_days-1', 'auction_vehicles-time_periods-1', 'auction_vehicles-preview_site-1', 'auction_vehicles-the_doors-1', 'auction_vehicles-the_weight-1', 'auction_vehicles-input_time-1', 'auction_vehicles-inspection_report_media-1', 1, 1000.00, '2026-01-01 09:00:00', 'auction_vehicles-payment_method-1', 'auction_vehicles-transaction_ref-1', 'fixtures/auction_vehicles/1.jpg', 1, '2026-01-01 09:00:00', 'test', 'fixtures/auction_vehicles/1.jpg', 'test', 'test', 'test', 0, 'auction_vehicles-par', 1, '2026-01-01 09:00:00', 'auction_vehicles-partner_decided_by-1', 'auction_vehicles-claim_number-1'),
(2, 2, 2, 'auction_vehicles-lot_number-2', 'تجريبي 2 — auction_vehicles', 'auction_vehicles-make-2', 'auction_vehicles-model-2', 2, 2000.00, 'auction_vehicles-vehicle_condition-2', 'بيانات اختبار مُصطنَعة (auction_vehicles)', 'auction_vehicles-vehicle_data-2', 'auction_vehicles-settings_override-2', 'auction_vehicles-override_settings-2', 'test', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'auction_vehicles-vehicle_brand-2', 2, 'auction_vehicles-mileage-2', 'auction_vehicles-the_color-2', 'auction_vehicles-Plate_number-2', 'test', 'auction_vehicles-chassis_number-2', 'auction_vehicles-insurance_company-2', 'auction_vehicles-overview-2', 'test', 'auction_vehicles-auto_bid-2', 2000.00, '300000000000002', 'auction_vehicles-inspection_days-2', 'auction_vehicles-time_periods-2', 'auction_vehicles-preview_site-2', 'auction_vehicles-the_doors-2', 'auction_vehicles-the_weight-2', 'auction_vehicles-input_time-2', 'auction_vehicles-inspection_report_media-2', 2, 2000.00, '2026-01-02 09:00:00', 'auction_vehicles-payment_method-2', 'auction_vehicles-transaction_ref-2', 'fixtures/auction_vehicles/2.jpg', 2, '2026-01-02 09:00:00', 'test', 'fixtures/auction_vehicles/2.jpg', 'test', 'test', 'test', 0, 'auction_vehicles-par', 2, '2026-01-02 09:00:00', 'auction_vehicles-partner_decided_by-2', 'auction_vehicles-claim_number-2'),
(3, 3, 3, 'auction_vehicles-lot_number-3', 'تجريبي 3 — auction_vehicles', 'auction_vehicles-make-3', 'auction_vehicles-model-3', 3, 3000.00, 'auction_vehicles-vehicle_condition-3', 'بيانات اختبار مُصطنَعة (auction_vehicles)', 'auction_vehicles-vehicle_data-3', 'auction_vehicles-settings_override-3', 'auction_vehicles-override_settings-3', 'test', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'auction_vehicles-vehicle_brand-3', 3, 'auction_vehicles-mileage-3', 'auction_vehicles-the_color-3', 'auction_vehicles-Plate_number-3', 'test', 'auction_vehicles-chassis_number-3', 'auction_vehicles-insurance_company-3', 'auction_vehicles-overview-3', 'test', 'auction_vehicles-auto_bid-3', 3000.00, '300000000000003', 'auction_vehicles-inspection_days-3', 'auction_vehicles-time_periods-3', 'auction_vehicles-preview_site-3', 'auction_vehicles-the_doors-3', 'auction_vehicles-the_weight-3', 'auction_vehicles-input_time-3', 'auction_vehicles-inspection_report_media-3', 3, 3000.00, '2026-01-03 09:00:00', 'auction_vehicles-payment_method-3', 'auction_vehicles-transaction_ref-3', 'fixtures/auction_vehicles/3.jpg', 3, '2026-01-03 09:00:00', 'test', 'fixtures/auction_vehicles/3.jpg', 'test', 'test', 'test', 0, 'auction_vehicles-par', 3, '2026-01-03 09:00:00', 'auction_vehicles-partner_decided_by-3', 'auction_vehicles-claim_number-3');

INSERT INTO `auction_vehicles_preend_20260606_185855` (`id`, `auction_id`, `campaign_id`, `lot_number`, `vehicle_name`, `make`, `model`, `year`, `starting_price`, `vehicle_condition`, `condition_notes`, `vehicle_data`, `settings_override`, `override_settings`, `status`, `created_at`, `updated_at`, `vehicle_brand`, `year_of_manufacture`, `mileage`, `the_color`, `Plate_number`, `chassis_number`, `insurance_company`, `overview`, `mvpi_status`, `auto_bid`, `bidamount`, `activation_status`, `inspection_days`, `time_periods`, `preview_site`, `the_doors`, `the_weight`, `input_time`, `inspection_report_media`, `winner_user_id`, `final_price`, `winner_paid_at`, `payment_method`, `transaction_ref`, `receipt_image_path`, `winning_bid_id`, `awarded_at`, `approval_status`, `display_image`, `fuel_type`, `runs_status`, `key_status`) VALUES
(1, 1, 1, 'auction_vehicles_preend_20260606_185855-lot_number-1', 'تجريبي 1 — auction_vehicles_preend_20260606_185855', 'auction_vehicles_preend_20260606_185855-make-1', 'auction_vehicles_preend_20260606_185855-model-1', 1, 1000.00, 'auction_vehicles_preend_20260606_185855-vehicle_condition-1', 'بيانات اختبار مُصطنَعة (auction_vehicles_preend_20260606_185855)', 'auction_vehicles_preend_20260606_185855-vehicle_data-1', 'auction_vehicles_preend_20260606_185855-settings_override-1', 'auction_vehicles_preend_20260606_185855-override_settings-1', 'test', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'auction_vehicles_preend_20260606_185855-vehicle_brand-1', 1, 'auction_vehicles_preend_20260606_185855-mileage-1', 'auction_vehicles_preend_20260606_185855-the_color-1', 'auction_vehicles_preend_20260606_185855-Plate_number-1', 'auction_vehicles_preend_20260606_185855-chassis_number-1', 'auction_vehicles_preend_20260606_185855-insurance_company-1', 'auction_vehicles_preend_20260606_185855-overview-1', 'test', 'auction_vehicles_preend_20260606_185855-auto_bid-1', 1000.00, '300000000000001', 'auction_vehicles_preend_20260606_185855-inspection_days-1', 'auction_vehicles_preend_20260606_185855-time_periods-1', 'auction_vehicles_preend_20260606_185855-preview_site-1', 'auction_vehicles_preend_20260606_185855-the_doors-1', 'auction_vehicles_preend_20260606_185855-the_weight-1', 'auction_vehicles_preend_20260606_185855-input_time-1', 'auction_vehicles_preend_20260606_185855-inspection_report_media-1', 1, 1000.00, '2026-01-01 09:00:00', 'auction_vehicles_preend_20260606_185855-payment_method-1', 'auction_vehicles_preend_20260606_185855-transaction_ref-1', 'fixtures/auction_vehicles_preend_20260606_185855/1.jpg', 1, '2026-01-01 09:00:00', 'test', 'fixtures/auction_vehicles_preend_20260606_185855/1.jpg', 'test', 'test', 'test'),
(2, 2, 2, 'auction_vehicles_preend_20260606_185855-lot_number-2', 'تجريبي 2 — auction_vehicles_preend_20260606_185855', 'auction_vehicles_preend_20260606_185855-make-2', 'auction_vehicles_preend_20260606_185855-model-2', 2, 2000.00, 'auction_vehicles_preend_20260606_185855-vehicle_condition-2', 'بيانات اختبار مُصطنَعة (auction_vehicles_preend_20260606_185855)', 'auction_vehicles_preend_20260606_185855-vehicle_data-2', 'auction_vehicles_preend_20260606_185855-settings_override-2', 'auction_vehicles_preend_20260606_185855-override_settings-2', 'test', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'auction_vehicles_preend_20260606_185855-vehicle_brand-2', 2, 'auction_vehicles_preend_20260606_185855-mileage-2', 'auction_vehicles_preend_20260606_185855-the_color-2', 'auction_vehicles_preend_20260606_185855-Plate_number-2', 'auction_vehicles_preend_20260606_185855-chassis_number-2', 'auction_vehicles_preend_20260606_185855-insurance_company-2', 'auction_vehicles_preend_20260606_185855-overview-2', 'test', 'auction_vehicles_preend_20260606_185855-auto_bid-2', 2000.00, '300000000000002', 'auction_vehicles_preend_20260606_185855-inspection_days-2', 'auction_vehicles_preend_20260606_185855-time_periods-2', 'auction_vehicles_preend_20260606_185855-preview_site-2', 'auction_vehicles_preend_20260606_185855-the_doors-2', 'auction_vehicles_preend_20260606_185855-the_weight-2', 'auction_vehicles_preend_20260606_185855-input_time-2', 'auction_vehicles_preend_20260606_185855-inspection_report_media-2', 2, 2000.00, '2026-01-02 09:00:00', 'auction_vehicles_preend_20260606_185855-payment_method-2', 'auction_vehicles_preend_20260606_185855-transaction_ref-2', 'fixtures/auction_vehicles_preend_20260606_185855/2.jpg', 2, '2026-01-02 09:00:00', 'test', 'fixtures/auction_vehicles_preend_20260606_185855/2.jpg', 'test', 'test', 'test'),
(3, 3, 3, 'auction_vehicles_preend_20260606_185855-lot_number-3', 'تجريبي 3 — auction_vehicles_preend_20260606_185855', 'auction_vehicles_preend_20260606_185855-make-3', 'auction_vehicles_preend_20260606_185855-model-3', 3, 3000.00, 'auction_vehicles_preend_20260606_185855-vehicle_condition-3', 'بيانات اختبار مُصطنَعة (auction_vehicles_preend_20260606_185855)', 'auction_vehicles_preend_20260606_185855-vehicle_data-3', 'auction_vehicles_preend_20260606_185855-settings_override-3', 'auction_vehicles_preend_20260606_185855-override_settings-3', 'test', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'auction_vehicles_preend_20260606_185855-vehicle_brand-3', 3, 'auction_vehicles_preend_20260606_185855-mileage-3', 'auction_vehicles_preend_20260606_185855-the_color-3', 'auction_vehicles_preend_20260606_185855-Plate_number-3', 'auction_vehicles_preend_20260606_185855-chassis_number-3', 'auction_vehicles_preend_20260606_185855-insurance_company-3', 'auction_vehicles_preend_20260606_185855-overview-3', 'test', 'auction_vehicles_preend_20260606_185855-auto_bid-3', 3000.00, '300000000000003', 'auction_vehicles_preend_20260606_185855-inspection_days-3', 'auction_vehicles_preend_20260606_185855-time_periods-3', 'auction_vehicles_preend_20260606_185855-preview_site-3', 'auction_vehicles_preend_20260606_185855-the_doors-3', 'auction_vehicles_preend_20260606_185855-the_weight-3', 'auction_vehicles_preend_20260606_185855-input_time-3', 'auction_vehicles_preend_20260606_185855-inspection_report_media-3', 3, 3000.00, '2026-01-03 09:00:00', 'auction_vehicles_preend_20260606_185855-payment_method-3', 'auction_vehicles_preend_20260606_185855-transaction_ref-3', 'fixtures/auction_vehicles_preend_20260606_185855/3.jpg', 3, '2026-01-03 09:00:00', 'test', 'fixtures/auction_vehicles_preend_20260606_185855/3.jpg', 'test', 'test', 'test');

INSERT INTO `auctions_claims` (`id`, `car_id`, `claim_number`, `registration_form`) VALUES
(1, 1, 'auctions_claims-claim_number-1', 'auctions_claims-registration_form-1'),
(2, 2, 'auctions_claims-claim_number-2', 'auctions_claims-registration_form-2'),
(3, 3, 'auctions_claims-claim_number-3', 'auctions_claims-registration_form-3');

INSERT INTO `audit_log` (`id`, `created_at`, `actor_id`, `actor_username`, `actor_role`, `action_key`, `entity_type`, `entity_id`, `message`, `ip`, `user_agent`, `meta`) VALUES
(1, '2026-01-01 09:00:00', 1, 'تجريبي 1 — audit_log', 'audit_log-actor_role-1', 'audit_log-action_key-1', 'test', 'audit_log-entity_id-1', 'بيانات اختبار مُصطنَعة (audit_log)', 'audit_log-ip-1', 'audit_log-user_agent-1', '{}'),
(2, '2026-01-02 09:00:00', 2, 'تجريبي 2 — audit_log', 'audit_log-actor_role-2', 'audit_log-action_key-2', 'test', 'audit_log-entity_id-2', 'بيانات اختبار مُصطنَعة (audit_log)', 'audit_log-ip-2', 'audit_log-user_agent-2', '{}'),
(3, '2026-01-03 09:00:00', 3, 'تجريبي 3 — audit_log', 'audit_log-actor_role-3', 'audit_log-action_key-3', 'test', 'audit_log-entity_id-3', 'بيانات اختبار مُصطنَعة (audit_log)', 'audit_log-ip-3', 'audit_log-user_agent-3', '{}');

INSERT INTO `auto_bids` (`id`, `user_id`, `auction_id`, `max_amount`, `created_at`) VALUES
(1, 1, 1, 1000.00, '2026-01-01 09:00:00'),
(2, 2, 2, 2000.00, '2026-01-02 09:00:00'),
(3, 3, 3, 3000.00, '2026-01-03 09:00:00');

INSERT INTO `av_status_bak_20260602` (`id`, `status`) VALUES
(1, 'test'),
(2, 'test'),
(3, 'test');

INSERT INTO `packages` (`id`, `name`, `price`, `description`, `type`, `created_at`, `no_car`, `active`) VALUES
(1, 'تجريبي 1 — packages', 1000.00, 'packages-description-1', '1', '2026-01-01 09:00:00', 1, 0),
(2, 'تجريبي 2 — packages', 2000.00, 'packages-description-2', '1', '2026-01-02 09:00:00', 2, 0),
(3, 'تجريبي 3 — packages', 3000.00, 'packages-description-3', '1', '2026-01-03 09:00:00', 3, 0);

INSERT INTO `userss` (`id`, `phone`, `verification_code`, `failed_attempts`, `last_attempt_time`, `block_status`, `code_expiry`, `identity_type`, `identity_number`, `type_of_account`, `tax_image`, `birth_date`, `arabic_name`, `cr_number`, `english_name`, `gender`, `email`, `identity_image`, `total_insurance_paid`, `purchases_balance`, `wallet`, `id_customer`, `active_auctions_count`, `password`, `last_resend_time`, `created_at`, `iban_account`, `commerce_image`, `company_image`, `national_address_image`, `passport_image`, `country`, `plot_number`, `blocked_until`, `id_package`, `address`, `zip`, `building_no`, `vat_number`, `street`, `district`, `state`, `profile_image`, `city`, `player_id`, `additional_no`, `fcm_token`, `session_token`, `mobile_verified`, `remember_token_hash`, `remember_token_expires_at`) VALUES
(1, '966500000001', '1111', 1, '2026-01-01 09:00:00', 'allowed', '2026-01-01 09:00:00', 'id', '1000000001', 'personal', 'fixtures/userss/1.jpg', '2026-01-01', 'تجريبي 1 — userss', '1010000001', 'تجريبي 1 — userss', 'male', 'test1@example.invalid', 'fixtures/userss/1.jpg', 1000.00, 1000.00, 1000.00, 'userss-id_customer-1', 1, 'NOT-A-REAL-SECRET-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'SA0000000000000000000001', 'fixtures/userss/1.jpg', 'fixtures/userss/1.jpg', 'fixtures/userss/1.jpg', 'fixtures/userss/1.jpg', 'userss-country-1', 'userss-plot_number-1', '2026-01-01 09:00:00', 1, 'userss-address-1', 'userss-zip-1', 'userss-building_no-1', '300000000000001', 'userss-street-1', 'userss-district-1', 'test', 'fixtures/userss/1.jpg', 'userss-city-1', 'userss-player_id-1', 'userss-add', 'NOT-A-REAL-SECRET-1', 'NOT-A-REAL-SECRET-1', 0, 'NOT-A-REAL-SECRET-1', '2026-01-01 09:00:00'),
(2, '966500000002', '2222', 2, '2026-01-02 09:00:00', 'allowed', '2026-01-02 09:00:00', 'id', '1000000002', 'personal', 'fixtures/userss/2.jpg', '2026-01-02', 'تجريبي 2 — userss', '1010000002', 'تجريبي 2 — userss', 'male', 'test2@example.invalid', 'fixtures/userss/2.jpg', 2000.00, 2000.00, 2000.00, 'userss-id_customer-2', 2, 'NOT-A-REAL-SECRET-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'SA0000000000000000000002', 'fixtures/userss/2.jpg', 'fixtures/userss/2.jpg', 'fixtures/userss/2.jpg', 'fixtures/userss/2.jpg', 'userss-country-2', 'userss-plot_number-2', '2026-01-02 09:00:00', 2, 'userss-address-2', 'userss-zip-2', 'userss-building_no-2', '300000000000002', 'userss-street-2', 'userss-district-2', 'test', 'fixtures/userss/2.jpg', 'userss-city-2', 'userss-player_id-2', 'userss-add', 'NOT-A-REAL-SECRET-2', 'NOT-A-REAL-SECRET-2', 0, 'NOT-A-REAL-SECRET-2', '2026-01-02 09:00:00'),
(3, '966500000003', '3333', 3, '2026-01-03 09:00:00', 'allowed', '2026-01-03 09:00:00', 'id', '1000000003', 'personal', 'fixtures/userss/3.jpg', '2026-01-03', 'تجريبي 3 — userss', '1010000003', 'تجريبي 3 — userss', 'male', 'test3@example.invalid', 'fixtures/userss/3.jpg', 3000.00, 3000.00, 3000.00, 'userss-id_customer-3', 3, 'NOT-A-REAL-SECRET-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'SA0000000000000000000003', 'fixtures/userss/3.jpg', 'fixtures/userss/3.jpg', 'fixtures/userss/3.jpg', 'fixtures/userss/3.jpg', 'userss-country-3', 'userss-plot_number-3', '2026-01-03 09:00:00', 3, 'userss-address-3', 'userss-zip-3', 'userss-building_no-3', '300000000000003', 'userss-street-3', 'userss-district-3', 'test', 'fixtures/userss/3.jpg', 'userss-city-3', 'userss-player_id-3', 'userss-add', 'NOT-A-REAL-SECRET-3', 'NOT-A-REAL-SECRET-3', 0, 'NOT-A-REAL-SECRET-3', '2026-01-03 09:00:00');

INSERT INTO `bank_transfers` (`id`, `user_id`, `full_name`, `transfer_date`, `receipt_image`, `amount`, `created_at`, `status`) VALUES
(1, 1, 'تجريبي 1 — bank_transfers', '2026-01-01', 'fixtures/bank_transfers/1.jpg', 1000.00, '2026-01-01 09:00:00', 'pending'),
(2, 2, 'تجريبي 2 — bank_transfers', '2026-01-02', 'fixtures/bank_transfers/2.jpg', 2000.00, '2026-01-02 09:00:00', 'pending'),
(3, 3, 'تجريبي 3 — bank_transfers', '2026-01-03', 'fixtures/bank_transfers/3.jpg', 3000.00, '2026-01-03 09:00:00', 'pending');

INSERT INTO `bid_edit_audit` (`id`, `bid_id`, `user_id`, `auction_id`, `vehicle_id`, `old_amount`, `new_amount`, `source`, `actor_id`, `actor_name`, `edited_at`) VALUES
(1, 1, 1, 1, 1, 1000.00, 1000.00, 'bid_edit_audit-sourc', 1, 'تجريبي 1 — bid_edit_audit', '2026-01-01 09:00:00'),
(2, 2, 2, 2, 2, 2000.00, 2000.00, 'bid_edit_audit-sourc', 2, 'تجريبي 2 — bid_edit_audit', '2026-01-02 09:00:00'),
(3, 3, 3, 3, 3, 3000.00, 3000.00, 'bid_edit_audit-sourc', 3, 'تجريبي 3 — bid_edit_audit', '2026-01-03 09:00:00');

INSERT INTO `bids` (`id`, `auction_id`, `user_id`, `amount`, `created_at`, `paid_amount`, `is_auto`, `offer_status`, `sms_sent`, `amount_with_vat`, `auction_name`, `status`, `vehicle_id`, `rank`) VALUES
(1, 1, 1, 1, '2026-01-01 09:00:00', 1000.00, 0, 'pending', 0, 1000.00, 1, 'active', 1, 1),
(2, 2, 2, 2, '2026-01-02 09:00:00', 2000.00, 0, 'pending', 0, 2000.00, 2, 'active', 2, 2),
(3, 3, 3, 3, '2026-01-03 09:00:00', 3000.00, 0, 'pending', 0, 3000.00, 3, 'active', 3, 3);

INSERT INTO `bids_backup_20260214` (`id`, `auction_id`, `user_id`, `amount`, `created_at`, `paid_amount`, `is_auto`, `offer_status`, `sms_sent`, `amount_with_vat`, `auction_name`, `status`) VALUES
(1, 1, 1, 1, '2026-01-01 09:00:00', 1000.00, 0, 'pending', 0, 1000.00, 1, 'active'),
(2, 2, 2, 2, '2026-01-02 09:00:00', 2000.00, 0, 'pending', 0, 2000.00, 2, 'active'),
(3, 3, 3, 3, '2026-01-03 09:00:00', 3000.00, 0, 'pending', 0, 3000.00, 3, 'active');

INSERT INTO `bids_backup_auction_name` (`id`, `auction_id`, `auction_name`) VALUES
(1, 1, 1),
(2, 2, 2),
(3, 3, 3);

INSERT INTO `bids_bak_20260812_152428_nidal` (`id`, `auction_id`, `user_id`, `amount`, `created_at`, `paid_amount`, `is_auto`, `offer_status`, `sms_sent`, `amount_with_vat`, `auction_name`, `status`, `vehicle_id`, `rank`) VALUES
(1, 1, 1, 1, '2026-01-01 09:00:00', 1000.00, 0, 'pending', 0, 1000.00, 1, 'active', 1, 1),
(2, 2, 2, 2, '2026-01-02 09:00:00', 2000.00, 0, 'pending', 0, 2000.00, 2, 'active', 2, 2),
(3, 3, 3, 3, '2026-01-03 09:00:00', 3000.00, 0, 'pending', 0, 3000.00, 3, 'active', 3, 3);

INSERT INTO `bids_bak_20260821_143655_mahmoud` (`id`, `auction_id`, `user_id`, `amount`, `created_at`, `paid_amount`, `is_auto`, `offer_status`, `sms_sent`, `amount_with_vat`, `auction_name`, `status`, `vehicle_id`, `rank`) VALUES
(1, 1, 1, 1, '2026-01-01 09:00:00', 1000.00, 0, 'pending', 0, 1000.00, 1, 'active', 1, 1),
(2, 2, 2, 2, '2026-01-02 09:00:00', 2000.00, 0, 'pending', 0, 2000.00, 2, 'active', 2, 2),
(3, 3, 3, 3, '2026-01-03 09:00:00', 3000.00, 0, 'pending', 0, 3000.00, 3, 'active', 3, 3);

INSERT INTO `bids_preend_20260606_185855` (`id`, `auction_id`, `user_id`, `amount`, `created_at`, `paid_amount`, `is_auto`, `offer_status`, `sms_sent`, `amount_with_vat`, `auction_name`, `status`, `vehicle_id`, `rank`) VALUES
(1, 1, 1, 1, '2026-01-01 09:00:00', 1000.00, 0, 'pending', 0, 1000.00, 1, 'active', 1, 1),
(2, 2, 2, 2, '2026-01-02 09:00:00', 2000.00, 0, 'pending', 0, 2000.00, 2, 'active', 2, 2),
(3, 3, 3, 3, '2026-01-03 09:00:00', 3000.00, 0, 'pending', 0, 3000.00, 3, 'active', 3, 3);

INSERT INTO `details` (`id`, `car_id`, `overview`, `vehicle_brand`, `model`, `mvpi_status`, `year_of_manufacture`, `chassis_number`, `the_color`, `the_doors`, `the_condition`, `the_weight`, `inspection_days`, `time_periods`, `preview_site`, `inspection_report_media`, `insurance_company`, `input_time`, `activation_status`, `Plate_number`, `bidamount`, `auto_bid`) VALUES
(1, 1, 'details-overview-1', 'details-vehicle_brand-1', 'details-model-1', 'test', 1, 'details-chassis_number-1', 'details-the_color-1', 'details-the_doors-1', 'details-the_condition-1', 'details-the_weight-1', 'details-inspection_days-1', 'details-time_periods-1', 'details-preview_site-1', 'details-inspection_report_media-1', 'details-insurance_company-1', 'details-input_time-1', 'active', 'details-Plate_number-1', 'details-bi', 'details-auto_bid-1'),
(2, 2, 'details-overview-2', 'details-vehicle_brand-2', 'details-model-2', 'test', 2, 'details-chassis_number-2', 'details-the_color-2', 'details-the_doors-2', 'details-the_condition-2', 'details-the_weight-2', 'details-inspection_days-2', 'details-time_periods-2', 'details-preview_site-2', 'details-inspection_report_media-2', 'details-insurance_company-2', 'details-input_time-2', 'active', 'details-Plate_number-2', 'details-bi', 'details-auto_bid-2'),
(3, 3, 'details-overview-3', 'details-vehicle_brand-3', 'details-model-3', 'test', 3, 'details-chassis_number-3', 'details-the_color-3', 'details-the_doors-3', 'details-the_condition-3', 'details-the_weight-3', 'details-inspection_days-3', 'details-time_periods-3', 'details-preview_site-3', 'details-inspection_report_media-3', 'details-insurance_company-3', 'details-input_time-3', 'active', 'details-Plate_number-3', 'details-bi', 'details-auto_bid-3');

INSERT INTO `car_images` (`id`, `id_details`, `image`, `uploaded_at`) VALUES
(1, 1, 'fixtures/car_images/1.jpg', '2026-01-01 09:00:00'),
(2, 2, 'fixtures/car_images/2.jpg', '2026-01-02 09:00:00'),
(3, 3, 'fixtures/car_images/3.jpg', '2026-01-03 09:00:00');

INSERT INTO `card_permissions` (`id`, `card_key`, `role`, `allowed`) VALUES
(1, 'card_permissions-card_key-1', 'card_permissions-role-1', 0),
(2, 'card_permissions-card_key-2', 'card_permissions-role-2', 0),
(3, 'card_permissions-card_key-3', 'card_permissions-role-3', 0);

INSERT INTO `cards` (`id`, `card_key`, `parent_key`, `section_key`, `title_ar`, `title_en`, `href`, `desc_ar`, `desc_en`, `sort_order`, `created_at`) VALUES
(1, 'cards-card_key-1', 'cards-parent_key-1', 'cards-section_key-1', 'تجريبي 1 — cards', 'تجريبي 1 — cards', 'cards-href-1', 'cards-desc_ar-1', 'cards-desc_en-1', 1, '2026-01-01 09:00:00'),
(2, 'cards-card_key-2', 'cards-parent_key-2', 'cards-section_key-2', 'تجريبي 2 — cards', 'تجريبي 2 — cards', 'cards-href-2', 'cards-desc_ar-2', 'cards-desc_en-2', 2, '2026-01-02 09:00:00'),
(3, 'cards-card_key-3', 'cards-parent_key-3', 'cards-section_key-3', 'تجريبي 3 — cards', 'تجريبي 3 — cards', 'cards-href-3', 'cards-desc_ar-3', 'cards-desc_en-3', 3, '2026-01-03 09:00:00');

INSERT INTO `categories` (`id`, `name`, `image`, `link`, `status`) VALUES
(1, 'تجريبي 1 — categories', 'fixtures/categories/1.jpg', 'categories-link-1', 0),
(2, 'تجريبي 2 — categories', 'fixtures/categories/2.jpg', 'categories-link-2', 0),
(3, 'تجريبي 3 — categories', 'fixtures/categories/3.jpg', 'categories-link-3', 0);

INSERT INTO `chat_agents` (`id`, `user_id`, `name`, `phone`, `email`, `is_online`, `created_at`, `updated_at`) VALUES
(1, 1, 'تجريبي 1 — chat_agents', '966500000001', 'test1@example.invalid', 0, '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 2, 'تجريبي 2 — chat_agents', '966500000002', 'test2@example.invalid', 0, '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 3, 'تجريبي 3 — chat_agents', '966500000003', 'test3@example.invalid', 0, '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `chat_departments` (`id`, `dept_key`, `name_ar`, `name_en`, `is_online`, `use_ai`, `sort_order`, `created_at`, `updated_at`) VALUES
(1, 'chat_departments-dept_key-1', 'تجريبي 1 — chat_departments', 'تجريبي 1 — chat_departments', 0, 0, 1, '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 'chat_departments-dept_key-2', 'تجريبي 2 — chat_departments', 'تجريبي 2 — chat_departments', 0, 0, 2, '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 'chat_departments-dept_key-3', 'تجريبي 3 — chat_departments', 'تجريبي 3 — chat_departments', 0, 0, 3, '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `chat_agent_departments` (`id`, `agent_id`, `department_id`) VALUES
(1, 1, 1),
(2, 2, 2),
(3, 3, 3);

INSERT INTO `chat_conversations` (`id`, `client_name`, `client_phone`, `client_email`, `dept_id`, `staff_id`, `status`, `client_token`, `created_at`) VALUES
(1, 'تجريبي 1 — chat_conversations', '966500000001', 'test1@example.invalid', 1, 1, 'open', 'NOT-A-REAL-SECRET-1', '2026-01-01 09:00:00'),
(2, 'تجريبي 2 — chat_conversations', '966500000002', 'test2@example.invalid', 2, 2, 'open', 'NOT-A-REAL-SECRET-2', '2026-01-02 09:00:00'),
(3, 'تجريبي 3 — chat_conversations', '966500000003', 'test3@example.invalid', 3, 3, 'open', 'NOT-A-REAL-SECRET-3', '2026-01-03 09:00:00');

INSERT INTO `chat_messages` (`id`, `conv_id`, `sender_type`, `body`, `attachment_path`, `attachment_name`, `created_at`) VALUES
(1, 1, 'client', 'chat_messages-body-1', 'fixtures/chat_messages/1.jpg', 'تجريبي 1 — chat_messages', '2026-01-01 09:00:00'),
(2, 2, 'client', 'chat_messages-body-2', 'fixtures/chat_messages/2.jpg', 'تجريبي 2 — chat_messages', '2026-01-02 09:00:00'),
(3, 3, 'client', 'chat_messages-body-3', 'fixtures/chat_messages/3.jpg', 'تجريبي 3 — chat_messages', '2026-01-03 09:00:00');

INSERT INTO `departments` (`id`, `slug`, `label`, `is_online`, `last_seen`, `note`, `preferred_channel`, `wa_number`, `tel_number`, `livechat_url`, `responsible_id`, `updated_by`, `updated_at`) VALUES
(1, 'departments-slug-1', 'departments-label-1', 0, '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (departments)', 'whatsapp', 'departments-wa_numbe', 'departments-tel_numb', 'fixtures/departments/1.jpg', 1, 'departments-updated_by-1', '2026-01-01 09:00:00'),
(2, 'departments-slug-2', 'departments-label-2', 0, '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (departments)', 'whatsapp', 'departments-wa_numbe', 'departments-tel_numb', 'fixtures/departments/2.jpg', 2, 'departments-updated_by-2', '2026-01-02 09:00:00'),
(3, 'departments-slug-3', 'departments-label-3', 0, '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (departments)', 'whatsapp', 'departments-wa_numbe', 'departments-tel_numb', 'fixtures/departments/3.jpg', 3, 'departments-updated_by-3', '2026-01-03 09:00:00');

INSERT INTO `staff` (`id`, `dept_id`, `name`, `username`, `avatar_url`, `wa_number`, `livechat_url`, `email`, `is_online`, `last_seen`, `note`, `created_at`) VALUES
(1, 1, 'تجريبي 1 — staff', 'تجريبي 1 — staff', 'fixtures/staff/1.jpg', 'staff-wa_number-1', 'fixtures/staff/1.jpg', 'test1@example.invalid', 0, '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (staff)', '2026-01-01 09:00:00'),
(2, 2, 'تجريبي 2 — staff', 'تجريبي 2 — staff', 'fixtures/staff/2.jpg', 'staff-wa_number-2', 'fixtures/staff/2.jpg', 'test2@example.invalid', 0, '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (staff)', '2026-01-02 09:00:00'),
(3, 3, 'تجريبي 3 — staff', 'تجريبي 3 — staff', 'fixtures/staff/3.jpg', 'staff-wa_number-3', 'fixtures/staff/3.jpg', 'test3@example.invalid', 0, '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (staff)', '2026-01-03 09:00:00');

INSERT INTO `chat_ratings` (`id`, `conv_id`, `staff_id`, `rating`, `comment`, `created_at`, `stars`) VALUES
(1, 1, 1, 1, 'chat_ratings-comment-1', '2026-01-01 09:00:00', 1),
(2, 2, 2, 2, 'chat_ratings-comment-2', '2026-01-02 09:00:00', 2),
(3, 3, 3, 3, 'chat_ratings-comment-3', '2026-01-03 09:00:00', 3);

INSERT INTO `chat_sessions` (`id`, `user_id`, `guest_name`, `session_token`, `department_id`, `lang`, `status`, `rating`, `feedback`, `created_at`, `updated_at`, `closed_at`) VALUES
(1, 1, 'تجريبي 1 — chat_sessions', 'NOT-A-REAL-SECRET-1', 1, 'chat_', 'open', 1, 'chat_sessions-feedback-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 2, 'تجريبي 2 — chat_sessions', 'NOT-A-REAL-SECRET-2', 2, 'chat_', 'open', 2, 'chat_sessions-feedback-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 3, 'تجريبي 3 — chat_sessions', 'NOT-A-REAL-SECRET-3', 3, 'chat_', 'open', 3, 'chat_sessions-feedback-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `chat_typing` (`conv_id`, `who`, `updated_at`) VALUES
(1, 'client', '2026-01-01 09:00:00'),
(2, 'client', '2026-01-02 09:00:00'),
(3, 'client', '2026-01-03 09:00:00');

INSERT INTO `companies` (`id`, `company_name`, `author_name`, `id_number`, `phone`, `country`, `city`, `reigaon`, `bulding`, `add_number`, `vat_number`, `image1`, `image2`, `image3`, `image4`, `created_at`) VALUES
(1, 'تجريبي 1 — companies', 'تجريبي 1 — companies', 'companies-id_number-1', 1, 'companies-country-1', 'companies-city-1', 'companies-reigaon-1', 'companies-bulding-1', 'companies-add_number-1', '300000000000001', 'fixtures/companies/1.jpg', 'fixtures/companies/1.jpg', 'fixtures/companies/1.jpg', 'fixtures/companies/1.jpg', '2026-01-01 09:00:00'),
(2, 'تجريبي 2 — companies', 'تجريبي 2 — companies', 'companies-id_number-2', 2, 'companies-country-2', 'companies-city-2', 'companies-reigaon-2', 'companies-bulding-2', 'companies-add_number-2', '300000000000002', 'fixtures/companies/2.jpg', 'fixtures/companies/2.jpg', 'fixtures/companies/2.jpg', 'fixtures/companies/2.jpg', '2026-01-02 09:00:00'),
(3, 'تجريبي 3 — companies', 'تجريبي 3 — companies', 'companies-id_number-3', 3, 'companies-country-3', 'companies-city-3', 'companies-reigaon-3', 'companies-bulding-3', 'companies-add_number-3', '300000000000003', 'fixtures/companies/3.jpg', 'fixtures/companies/3.jpg', 'fixtures/companies/3.jpg', 'fixtures/companies/3.jpg', '2026-01-03 09:00:00');

INSERT INTO `company_payment` (`id`, `claim_number`, `car_name`, `plate_number`, `model`, `chassis_number`, `net_compensation`, `percentage`, `amount_before_tax`, `tax_amount`, `total_with_tax`) VALUES
(1, 'company_payment-claim_number-1', 'تجريبي 1 — company_payment', 'company_payment-plate_number-1', 'company_payment-model-1', 'company_payment-chassis_number-1', 1000.00, 'company_pa', 1000.00, 1000.00, 1000.00),
(2, 'company_payment-claim_number-2', 'تجريبي 2 — company_payment', 'company_payment-plate_number-2', 'company_payment-model-2', 'company_payment-chassis_number-2', 2000.00, 'company_pa', 2000.00, 2000.00, 2000.00),
(3, 'company_payment-claim_number-3', 'تجريبي 3 — company_payment', 'company_payment-plate_number-3', 'company_payment-model-3', 'company_payment-chassis_number-3', 3000.00, 'company_pa', 3000.00, 3000.00, 3000.00);

INSERT INTO `conversation_ratings` (`id`, `conv_id`, `rating`, `comment`, `created_at`) VALUES
(1, 1, 1, 'conversation_ratings-comment-1', '2026-01-01 09:00:00'),
(2, 2, 2, 'conversation_ratings-comment-2', '2026-01-02 09:00:00'),
(3, 3, 3, 'conversation_ratings-comment-3', '2026-01-03 09:00:00');

INSERT INTO `conversations` (`id`, `dept_id`, `assigned_staff_id`, `client_name`, `client_phone`, `client_email`, `client_lang`, `client_session`, `client_token`, `status`, `started_at`, `ended_at`, `last_activity_at`) VALUES
(1, 1, 1, 'تجريبي 1 — conversations', '966500000001', 'test1@example.invalid', 'conve', 'conversations-client_session-1', 'NOT-A-REAL-SECRET-1', 'open', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 2, 2, 'تجريبي 2 — conversations', '966500000002', 'test2@example.invalid', 'conve', 'conversations-client_session-2', 'NOT-A-REAL-SECRET-2', 'open', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 3, 3, 'تجريبي 3 — conversations', '966500000003', 'test3@example.invalid', 'conve', 'conversations-client_session-3', 'NOT-A-REAL-SECRET-3', 'open', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `customer_features` (`id`, `id_customer`, `voice_auction`, `merchants_auction`, `note`, `created_at`, `updated_at`) VALUES
(1, 1, 0, 0, 'بيانات اختبار مُصطنَعة (customer_features)', '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 2, 0, 0, 'بيانات اختبار مُصطنَعة (customer_features)', '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 3, 0, 0, 'بيانات اختبار مُصطنَعة (customer_features)', '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `customer_links` (`id`, `odoo_customer_id`, `user_id`, `source`, `confidence`, `note`, `created_at`) VALUES
(1, 1, 1, 'customer_links-s', 'customer_lin', 'بيانات اختبار مُصطنَعة (customer_links)', '2026-01-01 09:00:00'),
(2, 2, 2, 'customer_links-s', 'customer_lin', 'بيانات اختبار مُصطنَعة (customer_links)', '2026-01-02 09:00:00'),
(3, 3, 3, 'customer_links-s', 'customer_lin', 'بيانات اختبار مُصطنَعة (customer_links)', '2026-01-03 09:00:00');

INSERT INTO `delivery_requests` (`id`, `user_id`, `recipient_name`, `order_date`, `receive_time`, `delivery_location`, `location_coords`, `status`, `status_note`, `created_at`, `updated_at`) VALUES
(1, 1, 'تجريبي 1 — delivery_requests', '2026-01-01', '2026-01-01 09:00:00', 'delivery_requests-delivery_location-1', 'delivery_requests-location_coords-1', 'test', 'بيانات اختبار مُصطنَعة (delivery_requests)', '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 2, 'تجريبي 2 — delivery_requests', '2026-01-02', '2026-01-02 09:00:00', 'delivery_requests-delivery_location-2', 'delivery_requests-location_coords-2', 'test', 'بيانات اختبار مُصطنَعة (delivery_requests)', '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 3, 'تجريبي 3 — delivery_requests', '2026-01-03', '2026-01-03 09:00:00', 'delivery_requests-delivery_location-3', 'delivery_requests-location_coords-3', 'test', 'بيانات اختبار مُصطنَعة (delivery_requests)', '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `dept_status` (`id`, `dept`, `label`, `is_online`, `last_seen`, `note`, `updated_by`, `updated_at`) VALUES
(1, 'support', 'dept_status-label-1', 0, '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (dept_status)', 'dept_status-updated_by-1', '2026-01-01 09:00:00'),
(2, 'sales', 'dept_status-label-2', 0, '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (dept_status)', 'dept_status-updated_by-2', '2026-01-02 09:00:00'),
(3, 'accounts', 'dept_status-label-3', 0, '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (dept_status)', 'dept_status-updated_by-3', '2026-01-03 09:00:00');

INSERT INTO `favorites` (`id`, `user_id`, `auction_id`, `vehicle_id`, `created_at`) VALUES
(1, 1, 1, 1, '2026-01-01 09:00:00'),
(2, 2, 2, 2, '2026-01-02 09:00:00'),
(3, 3, 3, 3, '2026-01-03 09:00:00');

INSERT INTO `fcm_tokens` (`id`, `token`) VALUES
(1, 'NOT-A-REAL-SECRET-1'),
(2, 'NOT-A-REAL-SECRET-2'),
(3, 'NOT-A-REAL-SECRET-3');

INSERT INTO `files` (`id`, `file_name`, `file_path`, `file_size`, `file_type`, `uploaded_at`) VALUES
(1, 'تجريبي 1 — files', 'fixtures/files/1.jpg', 1, 'test', '2026-01-01 09:00:00'),
(2, 'تجريبي 2 — files', 'fixtures/files/2.jpg', 2, 'test', '2026-01-02 09:00:00'),
(3, 'تجريبي 3 — files', 'fixtures/files/3.jpg', 3, 'test', '2026-01-03 09:00:00');

INSERT INTO `firebase_tokens` (`id`, `user_id`, `phone`, `token`, `platform`, `created_at`) VALUES
(1, 1, '966500000001', 'NOT-A-REAL-SECRET-1', 'android', '2026-01-01 09:00:00'),
(2, 2, '966500000002', 'NOT-A-REAL-SECRET-2', 'android', '2026-01-02 09:00:00'),
(3, 3, '966500000003', 'NOT-A-REAL-SECRET-3', 'android', '2026-01-03 09:00:00');

INSERT INTO `fix68_bak_deposits` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'fix68_bak_deposits-odoo_payment_id-1', 1, 'fix68_bak_deposits-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (fix68_bak_deposits)'),
(2, 2, 2000.00, 'test', 'fix68_bak_deposits-odoo_payment_id-2', 2, 'fix68_bak_deposits-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (fix68_bak_deposits)'),
(3, 3, 3000.00, 'test', 'fix68_bak_deposits-odoo_payment_id-3', 3, 'fix68_bak_deposits-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (fix68_bak_deposits)');

INSERT INTO `haraj_chat_departments` (`id`, `code`, `name_ar`, `name_en`, `is_online`, `created_at`) VALUES
(1, 'NOT-A-REAL-SECRET-1', 'تجريبي 1 — haraj_chat_departments', 'تجريبي 1 — haraj_chat_departments', 0, '2026-01-01 09:00:00'),
(2, 'NOT-A-REAL-SECRET-2', 'تجريبي 2 — haraj_chat_departments', 'تجريبي 2 — haraj_chat_departments', 0, '2026-01-02 09:00:00'),
(3, 'NOT-A-REAL-SECRET-3', 'تجريبي 3 — haraj_chat_departments', 'تجريبي 3 — haraj_chat_departments', 0, '2026-01-03 09:00:00');

INSERT INTO `haraj_chat_agents` (`id`, `name`, `username`, `password_hash`, `department_id`, `is_online`, `created_at`) VALUES
(1, 'تجريبي 1 — haraj_chat_agents', 'تجريبي 1 — haraj_chat_agents', 'NOT-A-REAL-SECRET-1', 1, 0, '2026-01-01 09:00:00'),
(2, 'تجريبي 2 — haraj_chat_agents', 'تجريبي 2 — haraj_chat_agents', 'NOT-A-REAL-SECRET-2', 2, 0, '2026-01-02 09:00:00'),
(3, 'تجريبي 3 — haraj_chat_agents', 'تجريبي 3 — haraj_chat_agents', 'NOT-A-REAL-SECRET-3', 3, 0, '2026-01-03 09:00:00');

INSERT INTO `haraj_chat_staff` (`id`, `username`, `full_name`, `password_hash`, `is_active`, `is_online`, `manual_online`, `work_start`, `work_end`, `last_seen`, `created_at`) VALUES
(1, 'تجريبي 1 — haraj_chat_staff', 'تجريبي 1 — haraj_chat_staff', 'NOT-A-REAL-SECRET-1', 0, 0, 0, '09:00:00', '09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 'تجريبي 2 — haraj_chat_staff', 'تجريبي 2 — haraj_chat_staff', 'NOT-A-REAL-SECRET-2', 0, 0, 0, '09:00:00', '09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 'تجريبي 3 — haraj_chat_staff', 'تجريبي 3 — haraj_chat_staff', 'NOT-A-REAL-SECRET-3', 0, 0, 0, '09:00:00', '09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `haraj_chat_conversations` (`id`, `session_id`, `user_id`, `user_name`, `department_code`, `staff_id`, `lang`, `created_at`, `closed_at`) VALUES
(1, 'haraj_chat_conversations-session_id-1', 1, 'تجريبي 1 — haraj_chat_conversations', 'NOT-A-REAL-SECRET-1', 1, 'ha', '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 'haraj_chat_conversations-session_id-2', 2, 'تجريبي 2 — haraj_chat_conversations', 'NOT-A-REAL-SECRET-2', 2, 'ha', '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 'haraj_chat_conversations-session_id-3', 3, 'تجريبي 3 — haraj_chat_conversations', 'NOT-A-REAL-SECRET-3', 3, 'ha', '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `haraj_chat_messages` (`id`, `session_id`, `sender_type`, `sender_id`, `message`, `department_code`, `is_read`, `conversation_id`, `sender`, `message_text`, `lang`, `created_at`) VALUES
(1, 1, 'user', 1, 'بيانات اختبار مُصطنَعة (haraj_chat_messages)', 'NOT-A-REAL-SECRET-1', 0, 1, 'user', 'بيانات اختبار مُصطنَعة (haraj_chat_messages)', 'ha', '2026-01-01 09:00:00'),
(2, 2, 'user', 2, 'بيانات اختبار مُصطنَعة (haraj_chat_messages)', 'NOT-A-REAL-SECRET-2', 0, 2, 'user', 'بيانات اختبار مُصطنَعة (haraj_chat_messages)', 'ha', '2026-01-02 09:00:00'),
(3, 3, 'user', 3, 'بيانات اختبار مُصطنَعة (haraj_chat_messages)', 'NOT-A-REAL-SECRET-3', 0, 3, 'user', 'بيانات اختبار مُصطنَعة (haraj_chat_messages)', 'ha', '2026-01-03 09:00:00');

INSERT INTO `haraj_chat_notifications` (`id`, `conversation_id`, `is_read`, `created_at`) VALUES
(1, 1, 0, '2026-01-01 09:00:00'),
(2, 2, 0, '2026-01-02 09:00:00'),
(3, 3, 0, '2026-01-03 09:00:00');

INSERT INTO `haraj_chat_ratings` (`id`, `conversation_id`, `rating`, `comment`, `created_at`) VALUES
(1, 1, 1, 'haraj_chat_ratings-comment-1', '2026-01-01 09:00:00'),
(2, 2, 2, 'haraj_chat_ratings-comment-2', '2026-01-02 09:00:00'),
(3, 3, 3, 'haraj_chat_ratings-comment-3', '2026-01-03 09:00:00');

INSERT INTO `haraj_departments` (`id`, `code`, `name_ar`, `name_en`, `is_online`, `sort_order`, `created_at`, `updated_at`) VALUES
(1, 'NOT-A-REAL-SECRET-1', 'تجريبي 1 — haraj_departments', 'تجريبي 1 — haraj_departments', 0, 1, '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 'NOT-A-REAL-SECRET-2', 'تجريبي 2 — haraj_departments', 'تجريبي 2 — haraj_departments', 0, 2, '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 'NOT-A-REAL-SECRET-3', 'تجريبي 3 — haraj_departments', 'تجريبي 3 — haraj_departments', 0, 3, '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `haraj_chat_sessions` (`id`, `session_token`, `user_id`, `user_name`, `language`, `department_code`, `status`, `rating`, `created_at`, `updated_at`, `last_message_at`) VALUES
(1, 'NOT-A-REAL-SECRET-1', 1, 'تجريبي 1 — haraj_chat_sessions', 'haraj', 1, 'open', 1, '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 'NOT-A-REAL-SECRET-2', 2, 'تجريبي 2 — haraj_chat_sessions', 'haraj', 2, 'open', 2, '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 'NOT-A-REAL-SECRET-3', 3, 'تجريبي 3 — haraj_chat_sessions', 'haraj', 3, 'open', 3, '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `haraj_chat_staff_departments` (`id`, `staff_id`, `department_code`) VALUES
(1, 1, 'NOT-A-REAL-SECRET-1'),
(2, 2, 'NOT-A-REAL-SECRET-2'),
(3, 3, 'NOT-A-REAL-SECRET-3');

INSERT INTO `haraj_conversation_meta` (`conversation_id`, `assigned_staff_id`, `rating`, `rated_at`, `closed_by_admin_id`, `closed_at`) VALUES
(1, 1, 1, '2026-01-01 09:00:00', 1, '2026-01-01 09:00:00'),
(2, 2, 2, '2026-01-02 09:00:00', 2, '2026-01-02 09:00:00'),
(3, 3, 3, '2026-01-03 09:00:00', 3, '2026-01-03 09:00:00');

INSERT INTO `haraj_staff` (`id`, `username`, `password`, `full_name`, `phone`, `department_code`, `is_active`, `work_start`, `work_end`, `is_online`, `last_seen`, `created_at`, `updated_at`) VALUES
(1, 'تجريبي 1 — haraj_staff', 'NOT-A-REAL-SECRET-1', 'تجريبي 1 — haraj_staff', '966500000001', 'NOT-A-REAL-SECRET-1', 0, '09:00:00', '09:00:00', 0, '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 'تجريبي 2 — haraj_staff', 'NOT-A-REAL-SECRET-2', 'تجريبي 2 — haraj_staff', '966500000002', 'NOT-A-REAL-SECRET-2', 0, '09:00:00', '09:00:00', 0, '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 'تجريبي 3 — haraj_staff', 'NOT-A-REAL-SECRET-3', 'تجريبي 3 — haraj_staff', '966500000003', 'NOT-A-REAL-SECRET-3', 0, '09:00:00', '09:00:00', 0, '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `haraj_support_tickets` (`id`, `user_id`, `department`, `priority`, `subject`, `message`, `status`, `created_at`) VALUES
(1, 1, 'haraj_support_tickets-department-1', 'haraj_support_ticket', 'haraj_support_tickets-subject-1', 'بيانات اختبار مُصطنَعة (haraj_support_tickets)', 'test', '2026-01-01 09:00:00'),
(2, 2, 'haraj_support_tickets-department-2', 'haraj_support_ticket', 'haraj_support_tickets-subject-2', 'بيانات اختبار مُصطنَعة (haraj_support_tickets)', 'test', '2026-01-02 09:00:00'),
(3, 3, 'haraj_support_tickets-department-3', 'haraj_support_ticket', 'haraj_support_tickets-subject-3', 'بيانات اختبار مُصطنَعة (haraj_support_tickets)', 'test', '2026-01-03 09:00:00');

INSERT INTO `hehewala` (`id`, `id_userss`, `sender_name`, `phone`, `receipt_image`, `status`, `created_at`) VALUES
(1, 1, 'تجريبي 1 — hehewala', '966500000001', 'fixtures/hehewala/1.jpg', 0, '2026-01-01 09:00:00'),
(2, 2, 'تجريبي 2 — hehewala', '966500000002', 'fixtures/hehewala/2.jpg', 0, '2026-01-02 09:00:00'),
(3, 3, 'تجريبي 3 — hehewala', '966500000003', 'fixtures/hehewala/3.jpg', 0, '2026-01-03 09:00:00');

INSERT INTO `home_showcase` (`id`, `type`, `title_ar`, `title_en`, `params`, `is_active`, `updated_at`, `created_at`) VALUES
(1, 'carousel', 'تجريبي 1 — home_showcase', 'تجريبي 1 — home_showcase', 'home_showcase-params-1', 0, '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 'carousel', 'تجريبي 2 — home_showcase', 'تجريبي 2 — home_showcase', 'home_showcase-params-2', 0, '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 'carousel', 'تجريبي 3 — home_showcase', 'تجريبي 3 — home_showcase', 'home_showcase-params-3', 0, '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `home_showcase_items` (`id`, `showcase_id`, `image`, `link`, `caption`, `sort_order`, `created_at`) VALUES
(1, 1, 'fixtures/home_showcase_items/1.jpg', 'home_showcase_items-link-1', 'home_showcase_items-caption-1', 1, '2026-01-01 09:00:00'),
(2, 2, 'fixtures/home_showcase_items/2.jpg', 'home_showcase_items-link-2', 'home_showcase_items-caption-2', 2, '2026-01-02 09:00:00'),
(3, 3, 'fixtures/home_showcase_items/3.jpg', 'home_showcase_items-link-3', 'home_showcase_items-caption-3', 3, '2026-01-03 09:00:00');

INSERT INTO `insurance_cars` (`id`, `car_name`, `model_year`, `chassis_no`, `color`, `plate_no`, `claim_no`, `insurance_company`, `card_image`, `created_at`, `updated_at`) VALUES
(1, 'تجريبي 1 — insurance_cars', 1, 'insurance_cars-chassis_no-1', 'insurance_cars-color-1', 'insurance_cars-plate_no-1', 'insurance_cars-claim_no-1', 'insurance_cars-insurance_company-1', 'fixtures/insurance_cars/1.jpg', '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 'تجريبي 2 — insurance_cars', 2, 'insurance_cars-chassis_no-2', 'insurance_cars-color-2', 'insurance_cars-plate_no-2', 'insurance_cars-claim_no-2', 'insurance_cars-insurance_company-2', 'fixtures/insurance_cars/2.jpg', '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 'تجريبي 3 — insurance_cars', 3, 'insurance_cars-chassis_no-3', 'insurance_cars-color-3', 'insurance_cars-plate_no-3', 'insurance_cars-claim_no-3', 'insurance_cars-insurance_company-3', 'fixtures/insurance_cars/3.jpg', '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `insurance_companies` (`id`, `company_name`, `create_time`, `logo`) VALUES
(1, 'تجريبي 1 — insurance_companies', '2026-01-01 09:00:00', 'insurance_companies-logo-1'),
(2, 'تجريبي 2 — insurance_companies', '2026-01-02 09:00:00', 'insurance_companies-logo-2'),
(3, 'تجريبي 3 — insurance_companies', '2026-01-03 09:00:00', 'insurance_companies-logo-3');

INSERT INTO `insurance_deposits` (`id`, `user_id`, `amount`, `status`, `void_reason`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'بيانات اختبار مُصطنَعة (', 'insurance_deposits-odoo_payment_id-1', 1, 'insurance_deposits-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits)'),
(2, 2, 2000.00, 'test', 'بيانات اختبار مُصطنَعة (', 'insurance_deposits-odoo_payment_id-2', 2, 'insurance_deposits-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits)'),
(3, 3, 3000.00, 'test', 'بيانات اختبار مُصطنَعة (', 'insurance_deposits-odoo_payment_id-3', 3, 'insurance_deposits-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits)');

INSERT INTO `insurance_deposits_bak_20260620` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'insurance_deposits_bak_20260620-odoo_payment_id-1', 1, 'insurance_deposits_bak_20260620-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260620)'),
(2, 2, 2000.00, 'test', 'insurance_deposits_bak_20260620-odoo_payment_id-2', 2, 'insurance_deposits_bak_20260620-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260620)'),
(3, 3, 3000.00, 'test', 'insurance_deposits_bak_20260620-odoo_payment_id-3', 3, 'insurance_deposits_bak_20260620-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260620)');

INSERT INTO `insurance_deposits_bak_20260716_165410` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'insurance_deposits_bak_20260716_165410-odoo_payment_id-1', 1, 'insurance_deposits_bak_20260716_165410-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260716_165410)'),
(2, 2, 2000.00, 'test', 'insurance_deposits_bak_20260716_165410-odoo_payment_id-2', 2, 'insurance_deposits_bak_20260716_165410-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260716_165410)'),
(3, 3, 3000.00, 'test', 'insurance_deposits_bak_20260716_165410-odoo_payment_id-3', 3, 'insurance_deposits_bak_20260716_165410-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260716_165410)');

INSERT INTO `insurance_deposits_bak_20260717_190209` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'insurance_deposits_bak_20260717_190209-odoo_payment_id-1', 1, 'insurance_deposits_bak_20260717_190209-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260717_190209)'),
(2, 2, 2000.00, 'test', 'insurance_deposits_bak_20260717_190209-odoo_payment_id-2', 2, 'insurance_deposits_bak_20260717_190209-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260717_190209)'),
(3, 3, 3000.00, 'test', 'insurance_deposits_bak_20260717_190209-odoo_payment_id-3', 3, 'insurance_deposits_bak_20260717_190209-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260717_190209)');

INSERT INTO `insurance_deposits_bak_20260725_ajlan` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'insurance_deposits_bak_20260725_ajlan-odoo_payment_id-1', 1, 'insurance_deposits_bak_20260725_ajlan-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260725_ajlan)'),
(2, 2, 2000.00, 'test', 'insurance_deposits_bak_20260725_ajlan-odoo_payment_id-2', 2, 'insurance_deposits_bak_20260725_ajlan-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260725_ajlan)'),
(3, 3, 3000.00, 'test', 'insurance_deposits_bak_20260725_ajlan-odoo_payment_id-3', 3, 'insurance_deposits_bak_20260725_ajlan-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260725_ajlan)');

INSERT INTO `insurance_deposits_bak_20260725_muheet` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'insurance_deposits_bak_20260725_muheet-odoo_payment_id-1', 1, 'insurance_deposits_bak_20260725_muheet-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260725_muheet)'),
(2, 2, 2000.00, 'test', 'insurance_deposits_bak_20260725_muheet-odoo_payment_id-2', 2, 'insurance_deposits_bak_20260725_muheet-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260725_muheet)'),
(3, 3, 3000.00, 'test', 'insurance_deposits_bak_20260725_muheet-odoo_payment_id-3', 3, 'insurance_deposits_bak_20260725_muheet-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260725_muheet)');

INSERT INTO `insurance_deposits_bak_20260726_athyah` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'insurance_deposits_bak_20260726_athyah-odoo_payment_id-1', 1, 'insurance_deposits_bak_20260726_athyah-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260726_athyah)'),
(2, 2, 2000.00, 'test', 'insurance_deposits_bak_20260726_athyah-odoo_payment_id-2', 2, 'insurance_deposits_bak_20260726_athyah-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260726_athyah)'),
(3, 3, 3000.00, 'test', 'insurance_deposits_bak_20260726_athyah-odoo_payment_id-3', 3, 'insurance_deposits_bak_20260726_athyah-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260726_athyah)');

INSERT INTO `insurance_deposits_bak_20260726_overdebit` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'insurance_deposits_bak_20260726_overdebit-odoo_payment_id-1', 1, 'insurance_deposits_bak_20260726_overdebit-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260726_overdebit)'),
(2, 2, 2000.00, 'test', 'insurance_deposits_bak_20260726_overdebit-odoo_payment_id-2', 2, 'insurance_deposits_bak_20260726_overdebit-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260726_overdebit)'),
(3, 3, 3000.00, 'test', 'insurance_deposits_bak_20260726_overdebit-odoo_payment_id-3', 3, 'insurance_deposits_bak_20260726_overdebit-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260726_overdebit)');

INSERT INTO `insurance_deposits_bak_20260728_duplocks` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'insurance_deposits_bak_20260728_duplocks-odoo_payment_id-1', 1, 'insurance_deposits_bak_20260728_duplocks-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260728_duplocks)'),
(2, 2, 2000.00, 'test', 'insurance_deposits_bak_20260728_duplocks-odoo_payment_id-2', 2, 'insurance_deposits_bak_20260728_duplocks-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260728_duplocks)'),
(3, 3, 3000.00, 'test', 'insurance_deposits_bak_20260728_duplocks-odoo_payment_id-3', 3, 'insurance_deposits_bak_20260728_duplocks-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260728_duplocks)');

INSERT INTO `insurance_deposits_bak_20260729_missed2` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'insurance_deposits_bak_20260729_missed2-odoo_payment_id-1', 1, 'insurance_deposits_bak_20260729_missed2-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260729_missed2)'),
(2, 2, 2000.00, 'test', 'insurance_deposits_bak_20260729_missed2-odoo_payment_id-2', 2, 'insurance_deposits_bak_20260729_missed2-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260729_missed2)'),
(3, 3, 3000.00, 'test', 'insurance_deposits_bak_20260729_missed2-odoo_payment_id-3', 3, 'insurance_deposits_bak_20260729_missed2-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260729_missed2)');

INSERT INTO `insurance_deposits_bak_20260729_msuliman` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'insurance_deposits_bak_20260729_msuliman-odoo_payment_id-1', 1, 'insurance_deposits_bak_20260729_msuliman-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260729_msuliman)'),
(2, 2, 2000.00, 'test', 'insurance_deposits_bak_20260729_msuliman-odoo_payment_id-2', 2, 'insurance_deposits_bak_20260729_msuliman-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260729_msuliman)'),
(3, 3, 3000.00, 'test', 'insurance_deposits_bak_20260729_msuliman-odoo_payment_id-3', 3, 'insurance_deposits_bak_20260729_msuliman-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260729_msuliman)');

INSERT INTO `insurance_deposits_bak_20260729_odoo_withdraw` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'insurance_deposits_bak_20260729_odoo_withdraw-odoo_payment_id-1', 1, 'insurance_deposits_bak_20260729_odoo_withdraw-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260729_odoo_withdraw)'),
(2, 2, 2000.00, 'test', 'insurance_deposits_bak_20260729_odoo_withdraw-odoo_payment_id-2', 2, 'insurance_deposits_bak_20260729_odoo_withdraw-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260729_odoo_withdraw)'),
(3, 3, 3000.00, 'test', 'insurance_deposits_bak_20260729_odoo_withdraw-odoo_payment_id-3', 3, 'insurance_deposits_bak_20260729_odoo_withdraw-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260729_odoo_withdraw)');

INSERT INTO `insurance_deposits_bak_20260812_151258_release3` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'insurance_deposits_bak_20260812_151258_release3-odoo_payment_id-', 1, 'insurance_deposits_bak_20260812_151258_release3-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260812_151258_release3)'),
(2, 2, 2000.00, 'test', 'insurance_deposits_bak_20260812_151258_release3-odoo_payment_id-', 2, 'insurance_deposits_bak_20260812_151258_release3-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260812_151258_release3)'),
(3, 3, 3000.00, 'test', 'insurance_deposits_bak_20260812_151258_release3-odoo_payment_id-', 3, 'insurance_deposits_bak_20260812_151258_release3-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260812_151258_release3)');

INSERT INTO `insurance_deposits_bak_20260812_152428_nidal` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'insurance_deposits_bak_20260812_152428_nidal-odoo_payment_id-1', 1, 'insurance_deposits_bak_20260812_152428_nidal-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260812_152428_nidal)'),
(2, 2, 2000.00, 'test', 'insurance_deposits_bak_20260812_152428_nidal-odoo_payment_id-2', 2, 'insurance_deposits_bak_20260812_152428_nidal-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260812_152428_nidal)'),
(3, 3, 3000.00, 'test', 'insurance_deposits_bak_20260812_152428_nidal-odoo_payment_id-3', 3, 'insurance_deposits_bak_20260812_152428_nidal-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260812_152428_nidal)');

INSERT INTO `insurance_deposits_bak_20260820_144954_voidreason` (`id`, `status`, `notes`) VALUES
(1, 'test', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260820_144954_voidreason)'),
(2, 'test', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260820_144954_voidreason)'),
(3, 'test', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260820_144954_voidreason)');

INSERT INTO `insurance_deposits_bak_20260820_154246_dupacct` (`id`, `user_id`, `amount`, `status`, `void_reason`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'بيانات اختبار مُصطنَعة (', 'insurance_deposits_bak_20260820_154246_dupacct-odoo_payment_id-1', 1, 'insurance_deposits_bak_20260820_154246_dupacct-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260820_154246_dupacct)'),
(2, 2, 2000.00, 'test', 'بيانات اختبار مُصطنَعة (', 'insurance_deposits_bak_20260820_154246_dupacct-odoo_payment_id-2', 2, 'insurance_deposits_bak_20260820_154246_dupacct-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260820_154246_dupacct)'),
(3, 3, 3000.00, 'test', 'بيانات اختبار مُصطنَعة (', 'insurance_deposits_bak_20260820_154246_dupacct-odoo_payment_id-3', 3, 'insurance_deposits_bak_20260820_154246_dupacct-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260820_154246_dupacct)');

INSERT INTO `insurance_deposits_bak_20260821_143655_mahmoud` (`id`, `user_id`, `amount`, `status`, `void_reason`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'بيانات اختبار مُصطنَعة (', 'insurance_deposits_bak_20260821_143655_mahmoud-odoo_payment_id-1', 1, 'insurance_deposits_bak_20260821_143655_mahmoud-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260821_143655_mahmoud)'),
(2, 2, 2000.00, 'test', 'بيانات اختبار مُصطنَعة (', 'insurance_deposits_bak_20260821_143655_mahmoud-odoo_payment_id-2', 2, 'insurance_deposits_bak_20260821_143655_mahmoud-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260821_143655_mahmoud)'),
(3, 3, 3000.00, 'test', 'بيانات اختبار مُصطنَعة (', 'insurance_deposits_bak_20260821_143655_mahmoud-odoo_payment_id-3', 3, 'insurance_deposits_bak_20260821_143655_mahmoud-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_bak_20260821_143655_mahmoud)');

INSERT INTO `insurance_deposits_fix_bak_20260718` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'insurance_deposits_fix_bak_20260718-odoo_payment_id-1', 1, 'insurance_deposits_fix_bak_20260718-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_fix_bak_20260718)'),
(2, 2, 2000.00, 'test', 'insurance_deposits_fix_bak_20260718-odoo_payment_id-2', 2, 'insurance_deposits_fix_bak_20260718-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_fix_bak_20260718)'),
(3, 3, 3000.00, 'test', 'insurance_deposits_fix_bak_20260718-odoo_payment_id-3', 3, 'insurance_deposits_fix_bak_20260718-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_fix_bak_20260718)');

INSERT INTO `insurance_deposits_preend_20260606_185855` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'insurance_deposits_preend_20260606_185855-odoo_payment_id-1', 1, 'insurance_deposits_preend_20260606_185855-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_preend_20260606_185855)'),
(2, 2, 2000.00, 'test', 'insurance_deposits_preend_20260606_185855-odoo_payment_id-2', 2, 'insurance_deposits_preend_20260606_185855-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_preend_20260606_185855)'),
(3, 3, 3000.00, 'test', 'insurance_deposits_preend_20260606_185855-odoo_payment_id-3', 3, 'insurance_deposits_preend_20260606_185855-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_deposits_preend_20260606_185855)');

INSERT INTO `insurance_payments` (`id`, `user_id`, `auction_id`, `amount`, `status`, `paid_at`, `refunded_at`, `notes`) VALUES
(1, 1, 1, 1000.00, 'active', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_payments)'),
(2, 2, 2, 2000.00, 'active', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_payments)'),
(3, 3, 3, 3000.00, 'active', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (insurance_payments)');

INSERT INTO `insurance_refund_shortfalls` (`id`, `refund_id`, `user_id`, `odoo_payment_id`, `amount`, `resolved_amount`, `status`, `reason`, `detected_at`, `last_checked_at`, `resolved_at`) VALUES
(1, 1, 1, 'insurance_refund_shortfalls-odoo_payment_id-1', 1000.00, 1000.00, 'test', 'بيانات اختبار مُصطنَعة (insurance_refund_shortfalls)', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 2, 2, 'insurance_refund_shortfalls-odoo_payment_id-2', 2000.00, 2000.00, 'test', 'بيانات اختبار مُصطنَعة (insurance_refund_shortfalls)', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 3, 3, 'insurance_refund_shortfalls-odoo_payment_id-3', 3000.00, 3000.00, 'test', 'بيانات اختبار مُصطنَعة (insurance_refund_shortfalls)', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `invoices` (`id`, `user_id`, `invoice_number`, `issue_date`, `total_amount`, `created_at`, `payment_status`, `amount_paid`, `auction_id`) VALUES
(1, 1, 'invoices-invoice_number-1', '2026-01-01 09:00:00', 1000.00, '2026-01-01 09:00:00', 'غير مدفوع', 1000.00, 1),
(2, 2, 'invoices-invoice_number-2', '2026-01-02 09:00:00', 2000.00, '2026-01-02 09:00:00', 'غير مدفوع', 2000.00, 2),
(3, 3, 'invoices-invoice_number-3', '2026-01-03 09:00:00', 3000.00, '2026-01-03 09:00:00', 'غير مدفوع', 3000.00, 3);

INSERT INTO `invoices_oddo1` (`id`, `customer_name`, `vat_number`, `mobile`, `email`, `address`, `car_model`, `car_color`, `plate_no`, `amount`, `odoo_invoice_id`, `created_at`, `transfer_image`, `status`, `auction_id`, `id_user`, `type_of_account`) VALUES
(1, 'تجريبي 1 — invoices_oddo1', '300000000000001', '966500000001', 'test1@example.invalid', 'invoices_oddo1-address-1', 'invoices_oddo1-car_model-1', 'invoices_oddo1-car_color-1', 'invoices_oddo1-plate', 1000.00, 1, '2026-01-01 09:00:00', 'fixtures/invoices_oddo1/1.jpg', 'pending', 1, 1, 'test'),
(2, 'تجريبي 2 — invoices_oddo1', '300000000000002', '966500000002', 'test2@example.invalid', 'invoices_oddo1-address-2', 'invoices_oddo1-car_model-2', 'invoices_oddo1-car_color-2', 'invoices_oddo1-plate', 2000.00, 2, '2026-01-02 09:00:00', 'fixtures/invoices_oddo1/2.jpg', 'pending', 2, 2, 'test'),
(3, 'تجريبي 3 — invoices_oddo1', '300000000000003', '966500000003', 'test3@example.invalid', 'invoices_oddo1-address-3', 'invoices_oddo1-car_model-3', 'invoices_oddo1-car_color-3', 'invoices_oddo1-plate', 3000.00, 3, '2026-01-03 09:00:00', 'fixtures/invoices_oddo1/3.jpg', 'pending', 3, 3, 'test');

INSERT INTO `invoices_odoo` (`id`, `invoice_id`, `customer_id`, `auction_id`, `car_plate`, `car_model`, `car_color`, `vehicle_brand`, `chasis_number`, `amount`, `status`, `created_at`, `invoice_number`, `id_user`, `PaymentStatus`, `fees_amount`, `total`, `source`, `odoo_record_id`, `vehicle_id`, `amount_residual`) VALUES
(1, 1, 1, 1, 'invoices_odoo-car_plate-1', 'invoices_odoo-car_model-1', 'invoices_odoo-car_color-1', 'invoices_odoo-vehicle_brand-1', 'invoices_odoo-chasis_number-1', 1000.00, 'test', '2026-01-01 09:00:00', 'invoices_odoo-invoice_number-1', 1, 'not paid', 1000.00, 1000.00, 'invoices_odoo-source-1', 1, 1, 1000.00),
(2, 2, 2, 2, 'invoices_odoo-car_plate-2', 'invoices_odoo-car_model-2', 'invoices_odoo-car_color-2', 'invoices_odoo-vehicle_brand-2', 'invoices_odoo-chasis_number-2', 2000.00, 'test', '2026-01-02 09:00:00', 'invoices_odoo-invoice_number-2', 2, 'not paid', 2000.00, 2000.00, 'invoices_odoo-source-2', 2, 2, 2000.00),
(3, 3, 3, 3, 'invoices_odoo-car_plate-3', 'invoices_odoo-car_model-3', 'invoices_odoo-car_color-3', 'invoices_odoo-vehicle_brand-3', 'invoices_odoo-chasis_number-3', 3000.00, 'test', '2026-01-03 09:00:00', 'invoices_odoo-invoice_number-3', 3, 'not paid', 3000.00, 3000.00, 'invoices_odoo-source-3', 3, 3, 3000.00);

INSERT INTO `invoices_odoo2` (`id`, `invoice_id`, `customer_id`, `auction_id`, `car_plate`, `car_model`, `car_color`, `vehicle_brand`, `chasis_number`, `amount`, `purchase_price`, `status`, `created_at`, `invoice_number`, `id_user`, `PaymentStatus`) VALUES
(1, 1, 1, 1, 'invoices_odoo2-car_plate-1', 'invoices_odoo2-car_model-1', 'invoices_odoo2-car_color-1', 'invoices_odoo2-vehicle_brand-1', 'invoices_odoo2-chasis_number-1', 1000.00, 1000.00, 'test', '2026-01-01 09:00:00', 'invoices_odoo2-invoice_number-1', 1, 'not paid'),
(2, 2, 2, 2, 'invoices_odoo2-car_plate-2', 'invoices_odoo2-car_model-2', 'invoices_odoo2-car_color-2', 'invoices_odoo2-vehicle_brand-2', 'invoices_odoo2-chasis_number-2', 2000.00, 2000.00, 'test', '2026-01-02 09:00:00', 'invoices_odoo2-invoice_number-2', 2, 'not paid'),
(3, 3, 3, 3, 'invoices_odoo2-car_plate-3', 'invoices_odoo2-car_model-3', 'invoices_odoo2-car_color-3', 'invoices_odoo2-vehicle_brand-3', 'invoices_odoo2-chasis_number-3', 3000.00, 3000.00, 'test', '2026-01-03 09:00:00', 'invoices_odoo2-invoice_number-3', 3, 'not paid');

INSERT INTO `invoices_odoo_bak_20260620` (`id`, `invoice_id`, `customer_id`, `auction_id`, `car_plate`, `car_model`, `car_color`, `vehicle_brand`, `chasis_number`, `amount`, `status`, `created_at`, `invoice_number`, `id_user`, `PaymentStatus`, `fees_amount`, `total`, `source`, `odoo_record_id`, `vehicle_id`, `amount_residual`) VALUES
(1, 1, 1, 1, 'invoices_odoo_bak_20260620-car_plate-1', 'invoices_odoo_bak_20260620-car_model-1', 'invoices_odoo_bak_20260620-car_color-1', 'invoices_odoo_bak_20260620-vehicle_brand-1', 'invoices_odoo_bak_20260620-chasis_number-1', 1000.00, 'test', '2026-01-01 09:00:00', 'invoices_odoo_bak_20260620-invoice_number-1', 1, 'not paid', 1000.00, 1000.00, 'invoices_odoo_bak_20260620-sou', 1, 1, 1000.00),
(2, 2, 2, 2, 'invoices_odoo_bak_20260620-car_plate-2', 'invoices_odoo_bak_20260620-car_model-2', 'invoices_odoo_bak_20260620-car_color-2', 'invoices_odoo_bak_20260620-vehicle_brand-2', 'invoices_odoo_bak_20260620-chasis_number-2', 2000.00, 'test', '2026-01-02 09:00:00', 'invoices_odoo_bak_20260620-invoice_number-2', 2, 'not paid', 2000.00, 2000.00, 'invoices_odoo_bak_20260620-sou', 2, 2, 2000.00),
(3, 3, 3, 3, 'invoices_odoo_bak_20260620-car_plate-3', 'invoices_odoo_bak_20260620-car_model-3', 'invoices_odoo_bak_20260620-car_color-3', 'invoices_odoo_bak_20260620-vehicle_brand-3', 'invoices_odoo_bak_20260620-chasis_number-3', 3000.00, 'test', '2026-01-03 09:00:00', 'invoices_odoo_bak_20260620-invoice_number-3', 3, 'not paid', 3000.00, 3000.00, 'invoices_odoo_bak_20260620-sou', 3, 3, 3000.00);

INSERT INTO `invoices_odoo_bak_20260728_backfill` (`id`, `invoice_id`, `customer_id`, `auction_id`, `car_plate`, `car_model`, `car_color`, `vehicle_brand`, `chasis_number`, `amount`, `status`, `created_at`, `invoice_number`, `id_user`, `PaymentStatus`, `fees_amount`, `total`, `source`, `odoo_record_id`, `vehicle_id`, `amount_residual`) VALUES
(1, 1, 1, 1, 'invoices_odoo_bak_20260728_backfill-car_plate-1', 'invoices_odoo_bak_20260728_backfill-car_model-1', 'invoices_odoo_bak_20260728_backfill-car_color-1', 'invoices_odoo_bak_20260728_backfill-vehicle_brand-', 'invoices_odoo_bak_20260728_backfill-chasis_number-1', 1000.00, 'test', '2026-01-01 09:00:00', 'invoices_odoo_bak_20260728_backfill-invoice_number', 1, 'not paid', 1000.00, 1000.00, 'invoices_odoo_bak_20260728_bac', 1, 1, 1000.00),
(2, 2, 2, 2, 'invoices_odoo_bak_20260728_backfill-car_plate-2', 'invoices_odoo_bak_20260728_backfill-car_model-2', 'invoices_odoo_bak_20260728_backfill-car_color-2', 'invoices_odoo_bak_20260728_backfill-vehicle_brand-', 'invoices_odoo_bak_20260728_backfill-chasis_number-2', 2000.00, 'test', '2026-01-02 09:00:00', 'invoices_odoo_bak_20260728_backfill-invoice_number', 2, 'not paid', 2000.00, 2000.00, 'invoices_odoo_bak_20260728_bac', 2, 2, 2000.00),
(3, 3, 3, 3, 'invoices_odoo_bak_20260728_backfill-car_plate-3', 'invoices_odoo_bak_20260728_backfill-car_model-3', 'invoices_odoo_bak_20260728_backfill-car_color-3', 'invoices_odoo_bak_20260728_backfill-vehicle_brand-', 'invoices_odoo_bak_20260728_backfill-chasis_number-3', 3000.00, 'test', '2026-01-03 09:00:00', 'invoices_odoo_bak_20260728_backfill-invoice_number', 3, 'not paid', 3000.00, 3000.00, 'invoices_odoo_bak_20260728_bac', 3, 3, 3000.00);

INSERT INTO `invoices_odoo_bak_20260801_stale` (`id`, `invoice_id`, `customer_id`, `auction_id`, `car_plate`, `car_model`, `car_color`, `vehicle_brand`, `chasis_number`, `amount`, `status`, `created_at`, `invoice_number`, `id_user`, `PaymentStatus`, `fees_amount`, `total`, `source`, `odoo_record_id`, `vehicle_id`, `amount_residual`) VALUES
(1, 1, 1, 1, 'invoices_odoo_bak_20260801_stale-car_plate-1', 'invoices_odoo_bak_20260801_stale-car_model-1', 'invoices_odoo_bak_20260801_stale-car_color-1', 'invoices_odoo_bak_20260801_stale-vehicle_brand-1', 'invoices_odoo_bak_20260801_stale-chasis_number-1', 1000.00, 'test', '2026-01-01 09:00:00', 'invoices_odoo_bak_20260801_stale-invoice_number-1', 1, 'not paid', 1000.00, 1000.00, 'invoices_odoo_bak_20260801_sta', 1, 1, 1000.00),
(2, 2, 2, 2, 'invoices_odoo_bak_20260801_stale-car_plate-2', 'invoices_odoo_bak_20260801_stale-car_model-2', 'invoices_odoo_bak_20260801_stale-car_color-2', 'invoices_odoo_bak_20260801_stale-vehicle_brand-2', 'invoices_odoo_bak_20260801_stale-chasis_number-2', 2000.00, 'test', '2026-01-02 09:00:00', 'invoices_odoo_bak_20260801_stale-invoice_number-2', 2, 'not paid', 2000.00, 2000.00, 'invoices_odoo_bak_20260801_sta', 2, 2, 2000.00),
(3, 3, 3, 3, 'invoices_odoo_bak_20260801_stale-car_plate-3', 'invoices_odoo_bak_20260801_stale-car_model-3', 'invoices_odoo_bak_20260801_stale-car_color-3', 'invoices_odoo_bak_20260801_stale-vehicle_brand-3', 'invoices_odoo_bak_20260801_stale-chasis_number-3', 3000.00, 'test', '2026-01-03 09:00:00', 'invoices_odoo_bak_20260801_stale-invoice_number-3', 3, 'not paid', 3000.00, 3000.00, 'invoices_odoo_bak_20260801_sta', 3, 3, 3000.00);

INSERT INTO `invoices_odoo_deleted_bak` (`id`, `invoice_id`, `customer_id`, `auction_id`, `car_plate`, `car_model`, `car_color`, `vehicle_brand`, `chasis_number`, `amount`, `status`, `created_at`, `invoice_number`, `id_user`, `PaymentStatus`, `fees_amount`, `total`, `source`, `odoo_record_id`, `vehicle_id`, `amount_residual`) VALUES
(1, 1, 1, 1, 'invoices_odoo_deleted_bak-car_plate-1', 'invoices_odoo_deleted_bak-car_model-1', 'invoices_odoo_deleted_bak-car_color-1', 'invoices_odoo_deleted_bak-vehicle_brand-1', 'invoices_odoo_deleted_bak-chasis_number-1', 1000.00, 'test', '2026-01-01 09:00:00', 'invoices_odoo_deleted_bak-invoice_number-1', 1, 'not paid', 1000.00, 1000.00, 'invoices_odoo_deleted_bak-sour', 1, 1, 1000.00),
(2, 2, 2, 2, 'invoices_odoo_deleted_bak-car_plate-2', 'invoices_odoo_deleted_bak-car_model-2', 'invoices_odoo_deleted_bak-car_color-2', 'invoices_odoo_deleted_bak-vehicle_brand-2', 'invoices_odoo_deleted_bak-chasis_number-2', 2000.00, 'test', '2026-01-02 09:00:00', 'invoices_odoo_deleted_bak-invoice_number-2', 2, 'not paid', 2000.00, 2000.00, 'invoices_odoo_deleted_bak-sour', 2, 2, 2000.00),
(3, 3, 3, 3, 'invoices_odoo_deleted_bak-car_plate-3', 'invoices_odoo_deleted_bak-car_model-3', 'invoices_odoo_deleted_bak-car_color-3', 'invoices_odoo_deleted_bak-vehicle_brand-3', 'invoices_odoo_deleted_bak-chasis_number-3', 3000.00, 'test', '2026-01-03 09:00:00', 'invoices_odoo_deleted_bak-invoice_number-3', 3, 'not paid', 3000.00, 3000.00, 'invoices_odoo_deleted_bak-sour', 3, 3, 3000.00);

INSERT INTO `invoices_odoo_late_dupe_purge_20260607` (`id`, `invoice_id`, `customer_id`, `auction_id`, `car_plate`, `car_model`, `car_color`, `vehicle_brand`, `chasis_number`, `amount`, `status`, `created_at`, `invoice_number`, `id_user`, `PaymentStatus`, `fees_amount`, `total`, `source`, `odoo_record_id`, `vehicle_id`, `amount_residual`) VALUES
(1, 1, 1, 1, 'invoices_odoo_late_dupe_purge_20260607-car_plate-1', 'invoices_odoo_late_dupe_purge_20260607-car_model-1', 'invoices_odoo_late_dupe_purge_20260607-car_color-1', 'invoices_odoo_late_dupe_purge_20260607-vehicle_bra', 'invoices_odoo_late_dupe_purge_20260607-chasis_number-1', 1000.00, 'test', '2026-01-01 09:00:00', 'invoices_odoo_late_dupe_purge_20260607-invoice_num', 1, 'not paid', 1000.00, 1000.00, 'invoices_odoo_late_dupe_purge_', 1, 1, 1000.00),
(2, 2, 2, 2, 'invoices_odoo_late_dupe_purge_20260607-car_plate-2', 'invoices_odoo_late_dupe_purge_20260607-car_model-2', 'invoices_odoo_late_dupe_purge_20260607-car_color-2', 'invoices_odoo_late_dupe_purge_20260607-vehicle_bra', 'invoices_odoo_late_dupe_purge_20260607-chasis_number-2', 2000.00, 'test', '2026-01-02 09:00:00', 'invoices_odoo_late_dupe_purge_20260607-invoice_num', 2, 'not paid', 2000.00, 2000.00, 'invoices_odoo_late_dupe_purge_', 2, 2, 2000.00),
(3, 3, 3, 3, 'invoices_odoo_late_dupe_purge_20260607-car_plate-3', 'invoices_odoo_late_dupe_purge_20260607-car_model-3', 'invoices_odoo_late_dupe_purge_20260607-car_color-3', 'invoices_odoo_late_dupe_purge_20260607-vehicle_bra', 'invoices_odoo_late_dupe_purge_20260607-chasis_number-3', 3000.00, 'test', '2026-01-03 09:00:00', 'invoices_odoo_late_dupe_purge_20260607-invoice_num', 3, 'not paid', 3000.00, 3000.00, 'invoices_odoo_late_dupe_purge_', 3, 3, 3000.00);

INSERT INTO `invoices_odoo_loopbak_20260606` (`id`, `invoice_id`, `customer_id`, `auction_id`, `car_plate`, `car_model`, `car_color`, `vehicle_brand`, `chasis_number`, `amount`, `status`, `created_at`, `invoice_number`, `id_user`, `PaymentStatus`, `fees_amount`, `total`, `source`, `odoo_record_id`, `vehicle_id`, `amount_residual`) VALUES
(1, 1, 1, 1, 'invoices_odoo_loopbak_20260606-car_plate-1', 'invoices_odoo_loopbak_20260606-car_model-1', 'invoices_odoo_loopbak_20260606-car_color-1', 'invoices_odoo_loopbak_20260606-vehicle_brand-1', 'invoices_odoo_loopbak_20260606-chasis_number-1', 1000.00, 'test', '2026-01-01 09:00:00', 'invoices_odoo_loopbak_20260606-invoice_number-1', 1, 'not paid', 1000.00, 1000.00, 'invoices_odoo_loopbak_20260606', 1, 1, 1000.00),
(2, 2, 2, 2, 'invoices_odoo_loopbak_20260606-car_plate-2', 'invoices_odoo_loopbak_20260606-car_model-2', 'invoices_odoo_loopbak_20260606-car_color-2', 'invoices_odoo_loopbak_20260606-vehicle_brand-2', 'invoices_odoo_loopbak_20260606-chasis_number-2', 2000.00, 'test', '2026-01-02 09:00:00', 'invoices_odoo_loopbak_20260606-invoice_number-2', 2, 'not paid', 2000.00, 2000.00, 'invoices_odoo_loopbak_20260606', 2, 2, 2000.00),
(3, 3, 3, 3, 'invoices_odoo_loopbak_20260606-car_plate-3', 'invoices_odoo_loopbak_20260606-car_model-3', 'invoices_odoo_loopbak_20260606-car_color-3', 'invoices_odoo_loopbak_20260606-vehicle_brand-3', 'invoices_odoo_loopbak_20260606-chasis_number-3', 3000.00, 'test', '2026-01-03 09:00:00', 'invoices_odoo_loopbak_20260606-invoice_number-3', 3, 'not paid', 3000.00, 3000.00, 'invoices_odoo_loopbak_20260606', 3, 3, 3000.00);

INSERT INTO `invoicesone` (`id`, `invoice_number`, `client_name`, `phone`, `email`, `account_type`, `car_name`, `model`, `vat_type`, `bid_amount`, `year_of_manufacture`, `color`, `plate_number`, `chassis_number`, `total_insurance_paid`, `created_at`, `amount_before_discount`, `subtotal`, `taxes`, `discount`, `total`, `amount_due`) VALUES
(1, 'invoicesone-invoice_number-1', 'تجريبي 1 — invoicesone', '966500000001', 'test1@example.invalid', 'test', 'تجريبي 1 — invoicesone', 'invoicesone-model-1', '300000000000001', 1000.00, 'invoiceson', 'invoicesone-color-1', 'invoicesone-plate_number-1', 'invoicesone-chassis_number-1', 1000.00, '2026-01-01 09:00:00', 1000.00, 1000.00, 1000.00, 1000.00, 1000.00, 1000.00),
(2, 'invoicesone-invoice_number-2', 'تجريبي 2 — invoicesone', '966500000002', 'test2@example.invalid', 'test', 'تجريبي 2 — invoicesone', 'invoicesone-model-2', '300000000000002', 2000.00, 'invoiceson', 'invoicesone-color-2', 'invoicesone-plate_number-2', 'invoicesone-chassis_number-2', 2000.00, '2026-01-02 09:00:00', 2000.00, 2000.00, 2000.00, 2000.00, 2000.00, 2000.00),
(3, 'invoicesone-invoice_number-3', 'تجريبي 3 — invoicesone', '966500000003', 'test3@example.invalid', 'test', 'تجريبي 3 — invoicesone', 'invoicesone-model-3', '300000000000003', 3000.00, 'invoiceson', 'invoicesone-color-3', 'invoicesone-plate_number-3', 'invoicesone-chassis_number-3', 3000.00, '2026-01-03 09:00:00', 3000.00, 3000.00, 3000.00, 3000.00, 3000.00, 3000.00);

INSERT INTO `invoicesonepayment` (`id`, `invoice_id`, `amount_paid`, `payment_date`) VALUES
(1, 1, 1000.00, '2026-01-01'),
(2, 2, 2000.00, '2026-01-02'),
(3, 3, 3000.00, '2026-01-03');

INSERT INTO `last2_20260805_bak` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'last2_20260805_bak-odoo_payment_id-1', 1, 'last2_20260805_bak-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (last2_20260805_bak)'),
(2, 2, 2000.00, 'test', 'last2_20260805_bak-odoo_payment_id-2', 2, 'last2_20260805_bak-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (last2_20260805_bak)'),
(3, 3, 3000.00, 'test', 'last2_20260805_bak-odoo_payment_id-3', 3, 'last2_20260805_bak-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (last2_20260805_bak)');

INSERT INTO `logs` (`id`, `user_id`, `activity`, `created_at`, `ip`, `country`, `region`, `city`, `block_status`) VALUES
(1, 1, 'logs-activity-1', '2026-01-01 09:00:00', 'logs-ip-1', 'logs-country-1', 'logs-region-1', 'logs-city-1', 'allowed'),
(2, 2, 'logs-activity-2', '2026-01-02 09:00:00', 'logs-ip-2', 'logs-country-2', 'logs-region-2', 'logs-city-2', 'allowed'),
(3, 3, 'logs-activity-3', '2026-01-03 09:00:00', 'logs-ip-3', 'logs-country-3', 'logs-region-3', 'logs-city-3', 'allowed');

INSERT INTO `management` (`id`, `username`, `role_key`, `password`, `is_active`, `created_at`, `phone`, `local_token_version`, `updated_at`) VALUES
(1, 'تجريبي 1 — management', 'management-role_key-1', 'NOT-A-REAL-SECRET-1', 0, '2026-01-01 09:00:00', '966500000001', 1, '2026-01-01 09:00:00'),
(2, 'تجريبي 2 — management', 'management-role_key-2', 'NOT-A-REAL-SECRET-2', 0, '2026-01-02 09:00:00', '966500000002', 2, '2026-01-02 09:00:00'),
(3, 'تجريبي 3 — management', 'management-role_key-3', 'NOT-A-REAL-SECRET-3', 0, '2026-01-03 09:00:00', '966500000003', 3, '2026-01-03 09:00:00');

INSERT INTO `management10` (`id`, `username`, `password`, `role`, `created_at`) VALUES
(1, 'تجريبي 1 — management10', 'NOT-A-REAL-SECRET-1', 'owner', '2026-01-01 09:00:00'),
(2, 'تجريبي 2 — management10', 'NOT-A-REAL-SECRET-2', 'owner', '2026-01-02 09:00:00'),
(3, 'تجريبي 3 — management10', 'NOT-A-REAL-SECRET-3', 'owner', '2026-01-03 09:00:00');

INSERT INTO `management_audit_log` (`id`, `actor_id`, `actor_username`, `action`, `target_id`, `target_username`, `ip`, `user_agent`, `meta`, `created_at`) VALUES
(1, 1, 'تجريبي 1 — management_audit_log', 'management_audit_log-action-1', 1, 'تجريبي 1 — management_audit_log', 'management_audit_log-ip-1', 'management_audit_log-user_agent-1', '{}', '2026-01-01 09:00:00'),
(2, 2, 'تجريبي 2 — management_audit_log', 'management_audit_log-action-2', 2, 'تجريبي 2 — management_audit_log', 'management_audit_log-ip-2', 'management_audit_log-user_agent-2', '{}', '2026-01-02 09:00:00'),
(3, 3, 'تجريبي 3 — management_audit_log', 'management_audit_log-action-3', 3, 'تجريبي 3 — management_audit_log', 'management_audit_log-ip-3', 'management_audit_log-user_agent-3', '{}', '2026-01-03 09:00:00');

INSERT INTO `management_card_overrides` (`id`, `management_id`, `card_key`, `can_view`, `can_edit`, `can_delete`, `created_at`) VALUES
(1, 1, 'management_card_overrides-card_key-1', 0, 0, 0, '2026-01-01 09:00:00'),
(2, 2, 'management_card_overrides-card_key-2', 0, 0, 0, '2026-01-02 09:00:00'),
(3, 3, 'management_card_overrides-card_key-3', 0, 0, 0, '2026-01-03 09:00:00');

INSERT INTO `management_old_backup_20260607` (`id`, `username`, `role_key`, `password`, `is_active`, `created_at`, `phone`, `local_token_version`, `updated_at`) VALUES
(1, 'تجريبي 1 — management_old_backup_20260607', 'management_old_backup_20260607-role_key-1', 'NOT-A-REAL-SECRET-1', 0, '2026-01-01 09:00:00', '966500000001', 1, '2026-01-01 09:00:00'),
(2, 'تجريبي 2 — management_old_backup_20260607', 'management_old_backup_20260607-role_key-2', 'NOT-A-REAL-SECRET-2', 0, '2026-01-02 09:00:00', '966500000002', 2, '2026-01-02 09:00:00'),
(3, 'تجريبي 3 — management_old_backup_20260607', 'management_old_backup_20260607-role_key-3', 'NOT-A-REAL-SECRET-3', 0, '2026-01-03 09:00:00', '966500000003', 3, '2026-01-03 09:00:00');

INSERT INTO `merchants_auctions_sheet` (`id`, `id_user`, `auction_id`, `name_of_auction`, `id_park`, `car_name`, `price_before_vat`, `created_at`) VALUES
(1, 1, 1, 'تجريبي 1 — merchants_auctions_sheet', 'merchants_auctions_sheet-id_park-1', 'تجريبي 1 — merchants_auctions_sheet', 1000.00, '2026-01-01 09:00:00'),
(2, 2, 2, 'تجريبي 2 — merchants_auctions_sheet', 'merchants_auctions_sheet-id_park-2', 'تجريبي 2 — merchants_auctions_sheet', 2000.00, '2026-01-02 09:00:00'),
(3, 3, 3, 'تجريبي 3 — merchants_auctions_sheet', 'merchants_auctions_sheet-id_park-3', 'تجريبي 3 — merchants_auctions_sheet', 3000.00, '2026-01-03 09:00:00');

INSERT INTO `merchants_sheet` (`id`, `user_id`, `auction_id`, `name_of_auction`, `id_park`, `car_name`, `price`, `price_with_vat`, `created_at`) VALUES
(1, 1, 1, 'تجريبي 1 — merchants_sheet', 'merchants_sheet-id_park-1', 'تجريبي 1 — merchants_sheet', 1000.00, 1000.00, '2026-01-01 09:00:00'),
(2, 2, 2, 'تجريبي 2 — merchants_sheet', 'merchants_sheet-id_park-2', 'تجريبي 2 — merchants_sheet', 2000.00, 2000.00, '2026-01-02 09:00:00'),
(3, 3, 3, 'تجريبي 3 — merchants_sheet', 'merchants_sheet-id_park-3', 'تجريبي 3 — merchants_sheet', 3000.00, 3000.00, '2026-01-03 09:00:00');

INSERT INTO `messages` (`id`, `conv_id`, `sender_type`, `staff_id`, `body`, `attachment_path`, `attachment_name`, `is_read`, `created_at`) VALUES
(1, 1, 'client', 1, 'messages-body-1', 'fixtures/messages/1.jpg', 'تجريبي 1 — messages', 0, '2026-01-01 09:00:00'),
(2, 2, 'client', 2, 'messages-body-2', 'fixtures/messages/2.jpg', 'تجريبي 2 — messages', 0, '2026-01-02 09:00:00'),
(3, 3, 'client', 3, 'messages-body-3', 'fixtures/messages/3.jpg', 'تجريبي 3 — messages', 0, '2026-01-03 09:00:00');

INSERT INTO `moyasar_payments` (`id`, `reference`, `status`, `amount`, `card_number`, `card_holder`, `card_brand`, `created_at`, `message`) VALUES
(1, 'moyasar_payments-reference-1', 'test', 1000.00, 'moyasar_payments-card_number-1', 'moyasar_payments-card_holder-1', 'moyasar_payments-card_brand-1', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (moyasar_payments)'),
(2, 'moyasar_payments-reference-2', 'test', 2000.00, 'moyasar_payments-card_number-2', 'moyasar_payments-card_holder-2', 'moyasar_payments-card_brand-2', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (moyasar_payments)'),
(3, 'moyasar_payments-reference-3', 'test', 3000.00, 'moyasar_payments-card_number-3', 'moyasar_payments-card_holder-3', 'moyasar_payments-card_brand-3', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (moyasar_payments)');

INSERT INTO `news_ticker` (`id`, `text_ar`, `text_en`, `start_at`, `end_at`, `is_active`, `created_at`, `updated_at`) VALUES
(1, 'news_ticker-text_ar-1', 'news_ticker-text_en-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 0, '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 'news_ticker-text_ar-2', 'news_ticker-text_en-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 0, '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 'news_ticker-text_ar-3', 'news_ticker-text_en-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 0, '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `notifications` (`id`, `user_id`, `message`, `created_at`, `is_read`, `type`) VALUES
(1, 1, 'بيانات اختبار مُصطنَعة (notifications)', '2026-01-01 09:00:00', 0, 'bid'),
(2, 2, 'بيانات اختبار مُصطنَعة (notifications)', '2026-01-02 09:00:00', 0, 'bid'),
(3, 3, 'بيانات اختبار مُصطنَعة (notifications)', '2026-01-03 09:00:00', 0, 'bid');

INSERT INTO `notifications_payment` (`id`, `user_id`, `invoice_id`, `message`, `created_at`, `payment_details`, `due_date`, `notification_type`) VALUES
(1, 1, 1, 'بيانات اختبار مُصطنَعة (notifications_payment)', '2026-01-01 09:00:00', 'notifications_payment-payment_details-1', '2026-01-01 09:00:00', 'unread'),
(2, 2, 2, 'بيانات اختبار مُصطنَعة (notifications_payment)', '2026-01-02 09:00:00', 'notifications_payment-payment_details-2', '2026-01-02 09:00:00', 'unread'),
(3, 3, 3, 'بيانات اختبار مُصطنَعة (notifications_payment)', '2026-01-03 09:00:00', 'notifications_payment-payment_details-3', '2026-01-03 09:00:00', 'unread');

INSERT INTO `odoo_customer_sync_pending` (`user_id`, `attempts`, `last_error`, `queued_at`, `updated_at`) VALUES
(1, 1, 'odoo_customer_sync_pending-last_error-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 2, 'odoo_customer_sync_pending-last_error-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 3, 'odoo_customer_sync_pending-last_error-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `odoo_inbox` (`id`, `endpoint`, `event`, `odoo_customer_id`, `odoo_payment_id`, `odoo_record_id`, `payment_ref`, `invoice_ref`, `amount`, `dedupe_key`, `payload`, `raw_body`, `status`, `resolved_user_id`, `legacy_http`, `legacy_result`, `legacy_response`, `legacy_at`, `received_at`, `resolve_note`, `last_try_at`, `try_count`, `applied_at`) VALUES
(1, 'odoo_inbox-endpoint-1', 'odoo_inbox-event-1', 1, 'odoo_inbox-odoo_payment_id-1', 'odoo_inbox-odoo_record_id-1', 'odoo_inbox-payment_ref-1', 'odoo_inbox-invoice_ref-1', 1000.00, 'odoo_inbox-dedupe_key-1', 'odoo_inbox-payload-1', 'odoo_inbox-raw_body-1', 'test', 1, 1, 'odoo_inbox-legacy_result-1', 'odoo_inbox-legacy_response-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (odoo_inbox)', '2026-01-01 09:00:00', 1, '2026-01-01 09:00:00'),
(2, 'odoo_inbox-endpoint-2', 'odoo_inbox-event-2', 2, 'odoo_inbox-odoo_payment_id-2', 'odoo_inbox-odoo_record_id-2', 'odoo_inbox-payment_ref-2', 'odoo_inbox-invoice_ref-2', 2000.00, 'odoo_inbox-dedupe_key-2', 'odoo_inbox-payload-2', 'odoo_inbox-raw_body-2', 'test', 2, 2, 'odoo_inbox-legacy_result-2', 'odoo_inbox-legacy_response-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (odoo_inbox)', '2026-01-02 09:00:00', 2, '2026-01-02 09:00:00'),
(3, 'odoo_inbox-endpoint-3', 'odoo_inbox-event-3', 3, 'odoo_inbox-odoo_payment_id-3', 'odoo_inbox-odoo_record_id-3', 'odoo_inbox-payment_ref-3', 'odoo_inbox-invoice_ref-3', 3000.00, 'odoo_inbox-dedupe_key-3', 'odoo_inbox-payload-3', 'odoo_inbox-raw_body-3', 'test', 3, 3, 'odoo_inbox-legacy_result-3', 'odoo_inbox-legacy_response-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (odoo_inbox)', '2026-01-03 09:00:00', 3, '2026-01-03 09:00:00');

INSERT INTO `odoo_logs` (`id`, `source`, `customer_id`, `payload`, `response`, `created_at`) VALUES
(1, 'odoo_logs-source-1', 1, 'odoo_logs-payload-1', 'odoo_logs-response-1', '2026-01-01 09:00:00'),
(2, 'odoo_logs-source-2', 2, 'odoo_logs-payload-2', 'odoo_logs-response-2', '2026-01-02 09:00:00'),
(3, 'odoo_logs-source-3', 3, 'odoo_logs-payload-3', 'odoo_logs-response-3', '2026-01-03 09:00:00');

INSERT INTO `odoo_payment_pushes` (`payment_reference`, `odoo_payment_id`, `amount`, `created_at`) VALUES
('odoo_payment_pushes-payment_reference-1', 'odoo_payment_pushes-odoo_payment_id-1', 1000.00, '2026-01-01 09:00:00'),
('odoo_payment_pushes-payment_reference-2', 'odoo_payment_pushes-odoo_payment_id-2', 2000.00, '2026-01-02 09:00:00'),
('odoo_payment_pushes-payment_reference-3', 'odoo_payment_pushes-odoo_payment_id-3', 3000.00, '2026-01-03 09:00:00');

INSERT INTO `office_qr_tokens` (`id`, `token`, `expires_at`, `created_at`) VALUES
(1, 'NOT-A-REAL-SECRET-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 'NOT-A-REAL-SECRET-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 'NOT-A-REAL-SECRET-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `otp_events` (`id`, `phone`, `ip`, `kind`, `created_at`) VALUES
(1, '966500000001', 'otp_events-ip-1', 'send', '2026-01-01 09:00:00'),
(2, '966500000002', 'otp_events-ip-2', 'send', '2026-01-02 09:00:00'),
(3, '966500000003', 'otp_events-ip-3', 'send', '2026-01-03 09:00:00');

INSERT INTO `paid_com` (`id`, `id_invoice`, `amount`, `paid`, `remain`, `total`, `status`, `image`) VALUES
(1, 1, 'paid_com-amount', 1, 1, 1, 'paid', 'fixtures/paid_com/1.jpg'),
(2, 2, 'paid_com-amount', 2, 2, 2, 'paid', 'fixtures/paid_com/2.jpg'),
(3, 3, 'paid_com-amount', 3, 3, 3, 'paid', 'fixtures/paid_com/3.jpg');

INSERT INTO `partial_payments` (`id`, `user_id`, `car_id`, `amount`, `payment_method`, `full_name`, `transfer_date`, `receipt_image`, `created_at`, `status`) VALUES
(1, 1, 1, 1000.00, 'partial_payments-payment_method-1', 'تجريبي 1 — partial_payments', '2026-01-01', 'fixtures/partial_payments/1.jpg', '2026-01-01 09:00:00', 'pending'),
(2, 2, 2, 2000.00, 'partial_payments-payment_method-2', 'تجريبي 2 — partial_payments', '2026-01-02', 'fixtures/partial_payments/2.jpg', '2026-01-02 09:00:00', 'pending'),
(3, 3, 3, 3000.00, 'partial_payments-payment_method-3', 'تجريبي 3 — partial_payments', '2026-01-03', 'fixtures/partial_payments/3.jpg', '2026-01-03 09:00:00', 'pending');

INSERT INTO `partner_payments` (`id`, `vehicle_id`, `amount`, `paid_at`, `note`, `receipt_path`, `batch_ref`, `created_by`, `created_at`) VALUES
(1, 1, 1000.00, '2026-01-01', 'بيانات اختبار مُصطنَعة (partner_payments)', 'fixtures/partner_payments/1.jpg', 'partner_payments-batch_ref-1', 'partner_payments-created_by-1', '2026-01-01 09:00:00'),
(2, 2, 2000.00, '2026-01-02', 'بيانات اختبار مُصطنَعة (partner_payments)', 'fixtures/partner_payments/2.jpg', 'partner_payments-batch_ref-2', 'partner_payments-created_by-2', '2026-01-02 09:00:00'),
(3, 3, 3000.00, '2026-01-03', 'بيانات اختبار مُصطنَعة (partner_payments)', 'fixtures/partner_payments/3.jpg', 'partner_payments-batch_ref-3', 'partner_payments-created_by-3', '2026-01-03 09:00:00');

INSERT INTO `payment_intents` (`id`, `user_id`, `gateway_payment_id`, `expected_amount`, `currency`, `purpose`, `created_at`) VALUES
(1, 1, 'payment_intents-gateway_payment_id-1', 1000.00, 'pay', 'subscription', '2026-01-01 09:00:00'),
(2, 2, 'payment_intents-gateway_payment_id-2', 2000.00, 'pay', 'subscription', '2026-01-02 09:00:00'),
(3, 3, 'payment_intents-gateway_payment_id-3', 3000.00, 'pay', 'subscription', '2026-01-03 09:00:00');

INSERT INTO `payments` (`id`, `payment_id`, `Mada`, `no_pch`, `user_id`, `amount`, `currency`, `status`, `description`, `created_at`, `odoo_payment_id`, `payment_name`, `state`) VALUES
(1, 'payments-payment_id-1', 'payments-Mada-1', 'payments-no_pch-1', 1, 1, 'payments-c', 'test', 'payments-description-1', '2026-01-01 09:00:00', 1, 'تجريبي 1 — payments', 'test'),
(2, 'payments-payment_id-2', 'payments-Mada-2', 'payments-no_pch-2', 2, 2, 'payments-c', 'test', 'payments-description-2', '2026-01-02 09:00:00', 2, 'تجريبي 2 — payments', 'test'),
(3, 'payments-payment_id-3', 'payments-Mada-3', 'payments-no_pch-3', 3, 3, 'payments-c', 'test', 'payments-description-3', '2026-01-03 09:00:00', 3, 'تجريبي 3 — payments', 'test');

INSERT INTO `payments_intents` (`id`, `user_id`, `customer_id`, `payment_code`, `expected_amount`, `created_at`, `expires_at`, `moyasar_payment_id`, `status`, `last_error`, `intent_token`) VALUES
(1, 1, 1, 'NOT-A-REAL-SECRET-1', 1000.00, '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'payments_intents-moyasar_payment_id-1', 'created', 'payments_intents-last_error-1', 'NOT-A-REAL-SECRET-1'),
(2, 2, 2, 'NOT-A-REAL-SECRET-2', 2000.00, '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'payments_intents-moyasar_payment_id-2', 'created', 'payments_intents-last_error-2', 'NOT-A-REAL-SECRET-2'),
(3, 3, 3, 'NOT-A-REAL-SECRET-3', 3000.00, '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'payments_intents-moyasar_payment_id-3', 'created', 'payments_intents-last_error-3', 'NOT-A-REAL-SECRET-3');

INSERT INTO `payments_odoo` (`id`, `payment_id`, `customer_id`, `amount`, `memo`, `payment_name`, `payment_code`, `status`, `created_at`, `invoice_id`, `payment_type`) VALUES
(1, 1, 1, 1000.00, 'بيانات اختبار مُصطنَعة (payments_odoo)', 'تجريبي 1 — payments_odoo', 'NOT-A-REAL-SECRET-1', 'test', '2026-01-01 09:00:00', 1, 'partial'),
(2, 2, 2, 2000.00, 'بيانات اختبار مُصطنَعة (payments_odoo)', 'تجريبي 2 — payments_odoo', 'NOT-A-REAL-SECRET-2', 'test', '2026-01-02 09:00:00', 2, 'partial'),
(3, 3, 3, 3000.00, 'بيانات اختبار مُصطنَعة (payments_odoo)', 'تجريبي 3 — payments_odoo', 'NOT-A-REAL-SECRET-3', 'test', '2026-01-03 09:00:00', 3, 'partial');

INSERT INTO `payments_test` (`id`, `customer_id`, `payment_code`, `amount`, `payment_reference`, `created_at`, `odoo_payment_id`, `payment_name`, `state`, `status`, `full_name`, `transfer_date`, `receipt_image_base64`, `moyasar_payment_id`, `attempts`, `last_error`) VALUES
(1, 1, 'NOT-A-REAL-SECRET-1', 1000.00, 'payments_test-payment_reference-1', '2026-01-01 09:00:00', 1, 'تجريبي 1 — payments_test', 'test', 'pending', 'تجريبي 1 — payments_test', '2026-01-01', 'fixtures/payments_test/1.jpg', 'payments_test-moyasar_payment_id-1', 1, 'payments_test-last_error-1'),
(2, 2, 'NOT-A-REAL-SECRET-2', 2000.00, 'payments_test-payment_reference-2', '2026-01-02 09:00:00', 2, 'تجريبي 2 — payments_test', 'test', 'pending', 'تجريبي 2 — payments_test', '2026-01-02', 'fixtures/payments_test/2.jpg', 'payments_test-moyasar_payment_id-2', 2, 'payments_test-last_error-2'),
(3, 3, 'NOT-A-REAL-SECRET-3', 3000.00, 'payments_test-payment_reference-3', '2026-01-03 09:00:00', 3, 'تجريبي 3 — payments_test', 'test', 'pending', 'تجريبي 3 — payments_test', '2026-01-03', 'fixtures/payments_test/3.jpg', 'payments_test-moyasar_payment_id-3', 3, 'payments_test-last_error-3');

INSERT INTO `phantom_20260805_bak` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'phantom_20260805_bak-odoo_payment_id-1', 1, 'phantom_20260805_bak-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (phantom_20260805_bak)'),
(2, 2, 2000.00, 'test', 'phantom_20260805_bak-odoo_payment_id-2', 2, 'phantom_20260805_bak-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (phantom_20260805_bak)'),
(3, 3, 3000.00, 'test', 'phantom_20260805_bak-odoo_payment_id-3', 3, 'phantom_20260805_bak-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (phantom_20260805_bak)');

INSERT INTO `plate_delivery_management` (`id`, `invoice_id`, `invoice_number`, `car_name`, `car_plate`, `car_model`, `customer_id`, `user_id`, `customer_name`, `customer_phone`, `drawer_number`, `sale_date`, `car_received_at`, `plates_received_at`, `ownership_transferred_at`, `transport_proof_file`, `plate_delivery_status`, `notes`, `created_at`, `updated_at`) VALUES
(1, 1, 'plate_delivery_management-invoice_number-1', 'تجريبي 1 — plate_delivery_management', 'plate_delivery_management-car_plate-1', 'plate_delivery_management-car_model-1', 1, 1, 'تجريبي 1 — plate_delivery_management', '966500000001', 'plate_delivery_management-drawer_number-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'plate_delivery_management-transport_proof_file-1', 'pending', 'بيانات اختبار مُصطنَعة (plate_delivery_management)', '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 2, 'plate_delivery_management-invoice_number-2', 'تجريبي 2 — plate_delivery_management', 'plate_delivery_management-car_plate-2', 'plate_delivery_management-car_model-2', 2, 2, 'تجريبي 2 — plate_delivery_management', '966500000002', 'plate_delivery_management-drawer_number-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'plate_delivery_management-transport_proof_file-2', 'pending', 'بيانات اختبار مُصطنَعة (plate_delivery_management)', '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 3, 'plate_delivery_management-invoice_number-3', 'تجريبي 3 — plate_delivery_management', 'plate_delivery_management-car_plate-3', 'plate_delivery_management-car_model-3', 3, 3, 'تجريبي 3 — plate_delivery_management', '966500000003', 'plate_delivery_management-drawer_number-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'plate_delivery_management-transport_proof_file-3', 'pending', 'بيانات اختبار مُصطنَعة (plate_delivery_management)', '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `products_stock` (`id`, `offer_name`, `avg_cost`, `total_value`, `qty_on_hand`, `svl_qty_layer`, `qty_available`, `incoming_qty`, `outgoing_qty`, `created_at`) VALUES
(1, 'تجريبي 1 — products_stock', 1000.00, 1000.00, 1, 1000.00, 1000.00, 1000.00, 1000.00, '2026-01-01 09:00:00'),
(2, 'تجريبي 2 — products_stock', 2000.00, 2000.00, 2, 2000.00, 2000.00, 2000.00, 2000.00, '2026-01-02 09:00:00'),
(3, 'تجريبي 3 — products_stock', 3000.00, 3000.00, 3, 3000.00, 3000.00, 3000.00, 3000.00, '2026-01-03 09:00:00');

INSERT INTO `pull_20260803_bak` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'pull_20260803_bak-odoo_payment_id-1', 1, 'pull_20260803_bak-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (pull_20260803_bak)'),
(2, 2, 2000.00, 'test', 'pull_20260803_bak-odoo_payment_id-2', 2, 'pull_20260803_bak-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (pull_20260803_bak)'),
(3, 3, 3000.00, 'test', 'pull_20260803_bak-odoo_payment_id-3', 3, 'pull_20260803_bak-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (pull_20260803_bak)');

INSERT INTO `purchases` (`id`, `user_id`, `auction_id`, `total_price`, `status`, `date`, `payment_method`, `notes`) VALUES
(1, 1, 1, 1000.00, 'تم الدفع', '2026-01-01 09:00:00', 'purchases-payment_method-1', 'بيانات اختبار مُصطنَعة (purchases)'),
(2, 2, 2, 2000.00, 'تم الدفع', '2026-01-02 09:00:00', 'purchases-payment_method-2', 'بيانات اختبار مُصطنَعة (purchases)'),
(3, 3, 3, 3000.00, 'تم الدفع', '2026-01-03 09:00:00', 'purchases-payment_method-3', 'بيانات اختبار مُصطنَعة (purchases)');

INSERT INTO `qomah_20260805_bak` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'qomah_20260805_bak-odoo_payment_id-1', 1, 'qomah_20260805_bak-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (qomah_20260805_bak)'),
(2, 2, 2000.00, 'test', 'qomah_20260805_bak-odoo_payment_id-2', 2, 'qomah_20260805_bak-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (qomah_20260805_bak)'),
(3, 3, 3000.00, 'test', 'qomah_20260805_bak-odoo_payment_id-3', 3, 'qomah_20260805_bak-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (qomah_20260805_bak)');

INSERT INTO `qr_codes` (`id`, `name`, `email`, `qr_code`, `created_at`) VALUES
(1, 'تجريبي 1 — qr_codes', 'test1@example.invalid', 'NOT-A-REAL-SECRET-1', '2026-01-01 09:00:00'),
(2, 'تجريبي 2 — qr_codes', 'test2@example.invalid', 'NOT-A-REAL-SECRET-2', '2026-01-02 09:00:00'),
(3, 'تجريبي 3 — qr_codes', 'test3@example.invalid', 'NOT-A-REAL-SECRET-3', '2026-01-03 09:00:00');

INSERT INTO `queue_departments` (`id`, `name_ar`, `name_en`, `prefix`, `avg_service_minutes`, `is_active`, `created_at`) VALUES
(1, 'تجريبي 1 — queue_departments', 'تجريبي 1 — queue_departments', 'queue_depa', 1, 0, '2026-01-01 09:00:00'),
(2, 'تجريبي 2 — queue_departments', 'تجريبي 2 — queue_departments', 'queue_depa', 2, 0, '2026-01-02 09:00:00'),
(3, 'تجريبي 3 — queue_departments', 'تجريبي 3 — queue_departments', 'queue_depa', 3, 0, '2026-01-03 09:00:00');

INSERT INTO `queue_counters` (`id`, `department_id`, `employee_name`, `counter_name`, `is_online`, `created_at`) VALUES
(1, 1, 'تجريبي 1 — queue_counters', 'تجريبي 1 — queue_counters', 0, '2026-01-01 09:00:00'),
(2, 2, 'تجريبي 2 — queue_counters', 'تجريبي 2 — queue_counters', 0, '2026-01-02 09:00:00'),
(3, 3, 'تجريبي 3 — queue_counters', 'تجريبي 3 — queue_counters', 0, '2026-01-03 09:00:00');

INSERT INTO `queue_tickets` (`id`, `user_id`, `user_mobile`, `department_id`, `ticket_number`, `source`, `priority`, `status`, `qr_token`, `notes`, `called_at`, `service_started_at`, `finished_at`, `created_at`) VALUES
(1, 1, '966500000001', 1, 'queue_tickets-ticket_number-1', 'home', 'normal', 'waiting', 'NOT-A-REAL-SECRET-1', 'بيانات اختبار مُصطنَعة (queue_tickets)', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 2, '966500000002', 2, 'queue_tickets-ticket_number-2', 'home', 'normal', 'waiting', 'NOT-A-REAL-SECRET-2', 'بيانات اختبار مُصطنَعة (queue_tickets)', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 3, '966500000003', 3, 'queue_tickets-ticket_number-3', 'home', 'normal', 'waiting', 'NOT-A-REAL-SECRET-3', 'بيانات اختبار مُصطنَعة (queue_tickets)', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `recipient_id_images` (`id`, `exit_id`, `vehicle_id`, `recipient_name`, `recipient_id`, `recipient_phone`, `image_path`, `uploaded_by`, `created_at`) VALUES
(1, 1, 1, 'تجريبي 1 — recipient_id_images', 'recipient_id_images-recipient_id-1', '966500000001', 'fixtures/recipient_id_images/1.jpg', 'recipient_id_images-uploaded_by-1', '2026-01-01 09:00:00'),
(2, 2, 2, 'تجريبي 2 — recipient_id_images', 'recipient_id_images-recipient_id-2', '966500000002', 'fixtures/recipient_id_images/2.jpg', 'recipient_id_images-uploaded_by-2', '2026-01-02 09:00:00'),
(3, 3, 3, 'تجريبي 3 — recipient_id_images', 'recipient_id_images-recipient_id-3', '966500000003', 'fixtures/recipient_id_images/3.jpg', 'recipient_id_images-uploaded_by-3', '2026-01-03 09:00:00');

INSERT INTO `refund_requests` (`id`, `user_id`, `amount`, `status`, `processed`, `created_at`, `image`, `no_rin`) VALUES
(1, 1, 1000.00, 'pending', 0, '2026-01-01 09:00:00', 'fixtures/refund_requests/1.jpg', 'refund_requests-no_rin-1'),
(2, 2, 2000.00, 'pending', 0, '2026-01-02 09:00:00', 'fixtures/refund_requests/2.jpg', 'refund_requests-no_rin-2'),
(3, 3, 3000.00, 'pending', 0, '2026-01-03 09:00:00', 'fixtures/refund_requests/3.jpg', 'refund_requests-no_rin-3');

INSERT INTO `refunds_requests` (`id`, `customer_id`, `amount`, `memo`, `payment_code`, `created_at`, `odoo_payment_id`, `status`, `payment_name`, `payment_state`, `iban_image`, `requested_at`, `iban_account`, `deducted_at`) VALUES
(1, 1, 1000.00, 'بيانات اختبار مُصطنَعة (refunds_requests)', 'NOT-A-REAL-SECRET-1', '2026-01-01 09:00:00', 1, 'pending', 'تجريبي 1 — refunds_requests', 'test', 'fixtures/refunds_requests/1.jpg', '2026-01-01 09:00:00', 'SA0000000000000000000001', '2026-01-01 09:00:00'),
(2, 2, 2000.00, 'بيانات اختبار مُصطنَعة (refunds_requests)', 'NOT-A-REAL-SECRET-2', '2026-01-02 09:00:00', 2, 'pending', 'تجريبي 2 — refunds_requests', 'test', 'fixtures/refunds_requests/2.jpg', '2026-01-02 09:00:00', 'SA0000000000000000000002', '2026-01-02 09:00:00'),
(3, 3, 3000.00, 'بيانات اختبار مُصطنَعة (refunds_requests)', 'NOT-A-REAL-SECRET-3', '2026-01-03 09:00:00', 3, 'pending', 'تجريبي 3 — refunds_requests', 'test', 'fixtures/refunds_requests/3.jpg', '2026-01-03 09:00:00', 'SA0000000000000000000003', '2026-01-03 09:00:00');

INSERT INTO `requests` (`id`, `ip_address`, `timestamp`) VALUES
(1, 'requests-ip_address-1', '2026-01-01 09:00:00'),
(2, 'requests-ip_address-2', '2026-01-02 09:00:00'),
(3, 'requests-ip_address-3', '2026-01-03 09:00:00');

INSERT INTO `restore_20260805_bak` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'restore_20260805_bak-odoo_payment_id-1', 1, 'restore_20260805_bak-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (restore_20260805_bak)'),
(2, 2, 2000.00, 'test', 'restore_20260805_bak-odoo_payment_id-2', 2, 'restore_20260805_bak-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (restore_20260805_bak)'),
(3, 3, 3000.00, 'test', 'restore_20260805_bak-odoo_payment_id-3', 3, 'restore_20260805_bak-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (restore_20260805_bak)');

INSERT INTO `role_card_permissions` (`id`, `role_key`, `card_key`, `can_view`, `can_edit`, `can_delete`) VALUES
(1, 'role_card_permissions-role_key-1', 1, 0, 0, 0),
(2, 'role_card_permissions-role_key-2', 2, 0, 0, 0),
(3, 'role_card_permissions-role_key-3', 3, 0, 0, 0);

INSERT INTO `role_section_permissions` (`role_key`, `section_key`, `can_view`) VALUES
('role_section_permissions-role_key-1', 1, 0),
('role_section_permissions-role_key-2', 2, 0),
('role_section_permissions-role_key-3', 3, 0);

INSERT INTO `roles` (`id`, `role_key`, `role_name_ar`, `role_name_en`, `name`, `description`, `created_at`) VALUES
(1, 'roles-role_key-1', 'تجريبي 1 — roles', 'تجريبي 1 — roles', 'تجريبي 1 — roles', 'roles-description-1', '2026-01-01 09:00:00'),
(2, 'roles-role_key-2', 'تجريبي 2 — roles', 'تجريبي 2 — roles', 'تجريبي 2 — roles', 'roles-description-2', '2026-01-02 09:00:00'),
(3, 'roles-role_key-3', 'تجريبي 3 — roles', 'تجريبي 3 — roles', 'تجريبي 3 — roles', 'roles-description-3', '2026-01-03 09:00:00');

INSERT INTO `rubel_20260805_bak` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'rubel_20260805_bak-odoo_payment_id-1', 1, 'rubel_20260805_bak-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (rubel_20260805_bak)'),
(2, 2, 2000.00, 'test', 'rubel_20260805_bak-odoo_payment_id-2', 2, 'rubel_20260805_bak-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (rubel_20260805_bak)'),
(3, 3, 3000.00, 'test', 'rubel_20260805_bak-odoo_payment_id-3', 3, 'rubel_20260805_bak-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (rubel_20260805_bak)');

INSERT INTO `settings` (`id`, `site_name`, `site_description`, `site_keywords`, `site_logo`, `site_status`, `theme_mode`, `bg_color`, `text_color`, `btn_color`, `special_occasion_active`, `default_auction_type`) VALUES
(1, 'تجريبي 1 — settings', 'settings-site_description-1', 'settings-site_keywords-1', 'settings-site_logo-1', 0, 'settings-theme_mode-', 'settings-bg_color-1', 'settings-text_color-', 'settings-btn_color-1', 0, 'test'),
(2, 'تجريبي 2 — settings', 'settings-site_description-2', 'settings-site_keywords-2', 'settings-site_logo-2', 0, 'settings-theme_mode-', 'settings-bg_color-2', 'settings-text_color-', 'settings-btn_color-2', 0, 'test'),
(3, 'تجريبي 3 — settings', 'settings-site_description-3', 'settings-site_keywords-3', 'settings-site_logo-3', 0, 'settings-theme_mode-', 'settings-bg_color-3', 'settings-text_color-', 'settings-btn_color-3', 0, 'test');

INSERT INTO `shares` (`id`, `user_id`, `auction_id`, `shared_at`, `platform`) VALUES
(1, 1, 1, '2026-01-01 09:00:00', 'shares-platform-1'),
(2, 2, 2, '2026-01-02 09:00:00', 'shares-platform-2'),
(3, 3, 3, '2026-01-03 09:00:00', 'shares-platform-3');

INSERT INTO `sms_log` (`id`, `phone`, `sent_at`) VALUES
(1, '966500000001', '2026-01-01 09:00:00'),
(2, '966500000002', '2026-01-02 09:00:00'),
(3, '966500000003', '2026-01-03 09:00:00');

INSERT INTO `social_media` (`id`, `name`, `logo`, `link`, `text`, `is_active`, `created_at`) VALUES
(1, 'تجريبي 1 — social_media', 'social_media-logo-1', 'social_media-link-1', 'social_media-text-1', 0, '2026-01-01 09:00:00'),
(2, 'تجريبي 2 — social_media', 'social_media-logo-2', 'social_media-link-2', 'social_media-text-2', 0, '2026-01-02 09:00:00'),
(3, 'تجريبي 3 — social_media', 'social_media-logo-3', 'social_media-link-3', 'social_media-text-3', 0, '2026-01-03 09:00:00');

INSERT INTO `statistics` (`id`, `category`, `count`, `color`) VALUES
(1, 'statistics-category-1', 1, 'statist'),
(2, 'statistics-category-2', 2, 'statist'),
(3, 'statistics-category-3', 3, 'statist');

INSERT INTO `support_chat_sessions` (`id`, `user_id`, `department`, `status`, `created_at`, `closed_at`) VALUES
(1, 1, 'support', 'open', '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 2, 'support', 'open', '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 3, 'support', 'open', '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `support_messages` (`id`, `name`, `phone`, `email`, `message`, `ip`, `user_agent`, `status`, `created_at`) VALUES
(1, 'تجريبي 1 — support_messages', '966500000001', 'test1@example.invalid', 'بيانات اختبار مُصطنَعة (support_messages)', 'support_messages-ip-1', 'support_messages-user_agent-1', 'new', '2026-01-01 09:00:00'),
(2, 'تجريبي 2 — support_messages', '966500000002', 'test2@example.invalid', 'بيانات اختبار مُصطنَعة (support_messages)', 'support_messages-ip-2', 'support_messages-user_agent-2', 'new', '2026-01-02 09:00:00'),
(3, 'تجريبي 3 — support_messages', '966500000003', 'test3@example.invalid', 'بيانات اختبار مُصطنَعة (support_messages)', 'support_messages-ip-3', 'support_messages-user_agent-3', 'new', '2026-01-03 09:00:00');

INSERT INTO `support_replies` (`id`, `message_id`, `admin_username`, `subject`, `body`, `sent_via`, `created_at`) VALUES
(1, 1, 'تجريبي 1 — support_replies', 'support_replies-subject-1', 'support_replies-body-1', 'email', '2026-01-01 09:00:00'),
(2, 2, 'تجريبي 2 — support_replies', 'support_replies-subject-2', 'support_replies-body-2', 'email', '2026-01-02 09:00:00'),
(3, 3, 'تجريبي 3 — support_replies', 'support_replies-subject-3', 'support_replies-body-3', 'email', '2026-01-03 09:00:00');

INSERT INTO `support_tickets` (`id`, `user_id`, `user_name`, `user_phone`, `department`, `priority`, `subject`, `message`, `status`, `admin_reply`, `assigned_admin`, `created_at`, `updated_at`) VALUES
(1, 1, 'تجريبي 1 — support_tickets', '966500000001', 'support', 'low', 'support_tickets-subject-1', 'بيانات اختبار مُصطنَعة (support_tickets)', 'open', 'support_tickets-admin_reply-1', 'support_tickets-assigned_admin-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 2, 'تجريبي 2 — support_tickets', '966500000002', 'support', 'low', 'support_tickets-subject-2', 'بيانات اختبار مُصطنَعة (support_tickets)', 'open', 'support_tickets-admin_reply-2', 'support_tickets-assigned_admin-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 3, 'تجريبي 3 — support_tickets', '966500000003', 'support', 'low', 'support_tickets-subject-3', 'بيانات اختبار مُصطنَعة (support_tickets)', 'open', 'support_tickets-admin_reply-3', 'support_tickets-assigned_admin-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `themes` (`id`, `name`, `code`, `bg_color`, `text_color`, `btn_color`, `is_active`) VALUES
(1, 'تجريبي 1 — themes', 'NOT-A-REAL-SECRET-1', 'themes-bg_color-1', 'themes-text_color-1', 'themes-btn_color-1', 0),
(2, 'تجريبي 2 — themes', 'NOT-A-REAL-SECRET-2', 'themes-bg_color-2', 'themes-text_color-2', 'themes-btn_color-2', 0),
(3, 'تجريبي 3 — themes', 'NOT-A-REAL-SECRET-3', 'themes-bg_color-3', 'themes-text_color-3', 'themes-btn_color-3', 0);

INSERT INTO `themes1` (`id`, `name`, `is_active`, `brand_color`, `chip_color`, `card_color`, `body_bg`, `text_color`, `radius_px`, `shadow_lvl`, `img_h`, `ticker_speed`, `updated_at`, `created_at`, `info_color`) VALUES
(1, 'تجريبي 1 — themes1', 0, 'themes1-b', 'themes1-c', 'themes1-c', 'themes1-b', 'themes1-t', 1, 1, 1, 1, '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'themes1-info_color-1'),
(2, 'تجريبي 2 — themes1', 0, 'themes1-b', 'themes1-c', 'themes1-c', 'themes1-b', 'themes1-t', 2, 2, 2, 2, '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'themes1-info_color-2'),
(3, 'تجريبي 3 — themes1', 0, 'themes1-b', 'themes1-c', 'themes1-c', 'themes1-b', 'themes1-t', 3, 3, 3, 3, '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'themes1-info_color-3');

INSERT INTO `transfer_requests` (`id`, `request_type`, `user_id`, `car_id`, `invoice_id`, `payment_method`, `amount`, `status`, `progress_step`, `status_note`, `notes`, `new_owner_id_path`, `new_owner_license_path`, `bank_account_number`, `bank_iban`, `bank_transfer_date`, `bank_sender_name`, `bank_transfer_image_path`, `created_at`, `updated_at`, `amount_approved`, `odoo_payment_id`, `receipt_path`, `admin_note`) VALUES
(1, 'test', 1, 1, 1, 'bank', 1000.00, 'pending', 'form', 'بيانات اختبار مُصطنَعة (transfer_requests)', 'بيانات اختبار مُصطنَعة (transfer_requests)', 'fixtures/transfer_requests/1.jpg', 'fixtures/transfer_requests/1.jpg', 'transfer_requests-bank_account_number-1', 'SA0000000000000000000001', '2026-01-01', 'تجريبي 1 — transfer_requests', 'fixtures/transfer_requests/1.jpg', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 1000.00, 'transfer_requests-odoo_payment_id-1', 'fixtures/transfer_requests/1.jpg', 'بيانات اختبار مُصطنَعة (transfer_requests)'),
(2, 'test', 2, 2, 2, 'bank', 2000.00, 'pending', 'form', 'بيانات اختبار مُصطنَعة (transfer_requests)', 'بيانات اختبار مُصطنَعة (transfer_requests)', 'fixtures/transfer_requests/2.jpg', 'fixtures/transfer_requests/2.jpg', 'transfer_requests-bank_account_number-2', 'SA0000000000000000000002', '2026-01-02', 'تجريبي 2 — transfer_requests', 'fixtures/transfer_requests/2.jpg', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 2000.00, 'transfer_requests-odoo_payment_id-2', 'fixtures/transfer_requests/2.jpg', 'بيانات اختبار مُصطنَعة (transfer_requests)'),
(3, 'test', 3, 3, 3, 'bank', 3000.00, 'pending', 'form', 'بيانات اختبار مُصطنَعة (transfer_requests)', 'بيانات اختبار مُصطنَعة (transfer_requests)', 'fixtures/transfer_requests/3.jpg', 'fixtures/transfer_requests/3.jpg', 'transfer_requests-bank_account_number-3', 'SA0000000000000000000003', '2026-01-03', 'تجريبي 3 — transfer_requests', 'fixtures/transfer_requests/3.jpg', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 3000.00, 'transfer_requests-odoo_payment_id-3', 'fixtures/transfer_requests/3.jpg', 'بيانات اختبار مُصطنَعة (transfer_requests)');

INSERT INTO `translation_options` (`id`, `translation_id`, `option_key`, `option_value_arabic`, `option_value_english`, `option_value_urdu`, `option_value_hindi`, `created_at`) VALUES
(1, 1, 'translation_options-option_key-1', 'translation_options-option_value_arabic-1', 'translation_options-option_value_english-1', 'translation_options-option_value_urdu-1', 'translation_options-option_value_hindi-1', '2026-01-01 09:00:00'),
(2, 2, 'translation_options-option_key-2', 'translation_options-option_value_arabic-2', 'translation_options-option_value_english-2', 'translation_options-option_value_urdu-2', 'translation_options-option_value_hindi-2', '2026-01-02 09:00:00'),
(3, 3, 'translation_options-option_key-3', 'translation_options-option_value_arabic-3', 'translation_options-option_value_english-3', 'translation_options-option_value_urdu-3', 'translation_options-option_value_hindi-3', '2026-01-03 09:00:00');

INSERT INTO `turn_bookings` (`id`, `user_id`, `phone`, `department`, `location`, `turn_type`, `notes`, `status`, `created_at`) VALUES
(1, 1, '966500000001', 'turn_bookings-department-1', 'turn_bookings-location-1', 'test', 'بيانات اختبار مُصطنَعة (turn_bookings)', 'test', '2026-01-01 09:00:00'),
(2, 2, '966500000002', 'turn_bookings-department-2', 'turn_bookings-location-2', 'test', 'بيانات اختبار مُصطنَعة (turn_bookings)', 'test', '2026-01-02 09:00:00'),
(3, 3, '966500000003', 'turn_bookings-department-3', 'turn_bookings-location-3', 'test', 'بيانات اختبار مُصطنَعة (turn_bookings)', 'test', '2026-01-03 09:00:00');

INSERT INTO `undo_11603_bak_bids` (`id`, `auction_id`, `user_id`, `amount`, `created_at`, `paid_amount`, `is_auto`, `offer_status`, `sms_sent`, `amount_with_vat`, `auction_name`, `status`, `vehicle_id`, `rank`) VALUES
(1, 1, 1, 1, '2026-01-01 09:00:00', 1000.00, 0, 'pending', 0, 1000.00, 1, 'active', 1, 1),
(2, 2, 2, 2, '2026-01-02 09:00:00', 2000.00, 0, 'pending', 0, 2000.00, 2, 'active', 2, 2),
(3, 3, 3, 3, '2026-01-03 09:00:00', 3000.00, 0, 'pending', 0, 3000.00, 3, 'active', 3, 3);

INSERT INTO `undo_11603_bak_vehicles` (`id`, `auction_id`, `campaign_id`, `lot_number`, `vehicle_name`, `make`, `model`, `year`, `starting_price`, `vehicle_condition`, `condition_notes`, `vehicle_data`, `settings_override`, `override_settings`, `status`, `created_at`, `updated_at`, `vehicle_brand`, `year_of_manufacture`, `mileage`, `the_color`, `Plate_number`, `plate_type`, `chassis_number`, `insurance_company`, `overview`, `mvpi_status`, `auto_bid`, `bidamount`, `activation_status`, `inspection_days`, `time_periods`, `preview_site`, `the_doors`, `the_weight`, `input_time`, `inspection_report_media`, `winner_user_id`, `final_price`, `winner_paid_at`, `payment_method`, `transaction_ref`, `receipt_image_path`, `winning_bid_id`, `awarded_at`, `approval_status`, `display_image`, `fuel_type`, `runs_status`, `key_status`) VALUES
(1, 1, 1, 'undo_11603_bak_vehicles-lot_number-1', 'تجريبي 1 — undo_11603_bak_vehicles', 'undo_11603_bak_vehicles-make-1', 'undo_11603_bak_vehicles-model-1', 1, 1000.00, 'undo_11603_bak_vehicles-vehicle_condition-1', 'بيانات اختبار مُصطنَعة (undo_11603_bak_vehicles)', 'undo_11603_bak_vehicles-vehicle_data-1', 'undo_11603_bak_vehicles-settings_override-1', 'undo_11603_bak_vehicles-override_settings-1', 'test', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'undo_11603_bak_vehicles-vehicle_brand-1', 1, 'undo_11603_bak_vehicles-mileage-1', 'undo_11603_bak_vehicles-the_color-1', 'undo_11603_bak_vehicles-Plate_number-1', 'test', 'undo_11603_bak_vehicles-chassis_number-1', 'undo_11603_bak_vehicles-insurance_company-1', 'undo_11603_bak_vehicles-overview-1', 'test', 'undo_11603_bak_vehicles-auto_bid-1', 1000.00, '300000000000001', 'undo_11603_bak_vehicles-inspection_days-1', 'undo_11603_bak_vehicles-time_periods-1', 'undo_11603_bak_vehicles-preview_site-1', 'undo_11603_bak_vehicles-the_doors-1', 'undo_11603_bak_vehicles-the_weight-1', 'undo_11603_bak_vehicles-input_time-1', 'undo_11603_bak_vehicles-inspection_report_media-1', 1, 1000.00, '2026-01-01 09:00:00', 'undo_11603_bak_vehicles-payment_method-1', 'undo_11603_bak_vehicles-transaction_ref-1', 'fixtures/undo_11603_bak_vehicles/1.jpg', 1, '2026-01-01 09:00:00', 'test', 'fixtures/undo_11603_bak_vehicles/1.jpg', 'test', 'test', 'test'),
(2, 2, 2, 'undo_11603_bak_vehicles-lot_number-2', 'تجريبي 2 — undo_11603_bak_vehicles', 'undo_11603_bak_vehicles-make-2', 'undo_11603_bak_vehicles-model-2', 2, 2000.00, 'undo_11603_bak_vehicles-vehicle_condition-2', 'بيانات اختبار مُصطنَعة (undo_11603_bak_vehicles)', 'undo_11603_bak_vehicles-vehicle_data-2', 'undo_11603_bak_vehicles-settings_override-2', 'undo_11603_bak_vehicles-override_settings-2', 'test', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'undo_11603_bak_vehicles-vehicle_brand-2', 2, 'undo_11603_bak_vehicles-mileage-2', 'undo_11603_bak_vehicles-the_color-2', 'undo_11603_bak_vehicles-Plate_number-2', 'test', 'undo_11603_bak_vehicles-chassis_number-2', 'undo_11603_bak_vehicles-insurance_company-2', 'undo_11603_bak_vehicles-overview-2', 'test', 'undo_11603_bak_vehicles-auto_bid-2', 2000.00, '300000000000002', 'undo_11603_bak_vehicles-inspection_days-2', 'undo_11603_bak_vehicles-time_periods-2', 'undo_11603_bak_vehicles-preview_site-2', 'undo_11603_bak_vehicles-the_doors-2', 'undo_11603_bak_vehicles-the_weight-2', 'undo_11603_bak_vehicles-input_time-2', 'undo_11603_bak_vehicles-inspection_report_media-2', 2, 2000.00, '2026-01-02 09:00:00', 'undo_11603_bak_vehicles-payment_method-2', 'undo_11603_bak_vehicles-transaction_ref-2', 'fixtures/undo_11603_bak_vehicles/2.jpg', 2, '2026-01-02 09:00:00', 'test', 'fixtures/undo_11603_bak_vehicles/2.jpg', 'test', 'test', 'test'),
(3, 3, 3, 'undo_11603_bak_vehicles-lot_number-3', 'تجريبي 3 — undo_11603_bak_vehicles', 'undo_11603_bak_vehicles-make-3', 'undo_11603_bak_vehicles-model-3', 3, 3000.00, 'undo_11603_bak_vehicles-vehicle_condition-3', 'بيانات اختبار مُصطنَعة (undo_11603_bak_vehicles)', 'undo_11603_bak_vehicles-vehicle_data-3', 'undo_11603_bak_vehicles-settings_override-3', 'undo_11603_bak_vehicles-override_settings-3', 'test', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'undo_11603_bak_vehicles-vehicle_brand-3', 3, 'undo_11603_bak_vehicles-mileage-3', 'undo_11603_bak_vehicles-the_color-3', 'undo_11603_bak_vehicles-Plate_number-3', 'test', 'undo_11603_bak_vehicles-chassis_number-3', 'undo_11603_bak_vehicles-insurance_company-3', 'undo_11603_bak_vehicles-overview-3', 'test', 'undo_11603_bak_vehicles-auto_bid-3', 3000.00, '300000000000003', 'undo_11603_bak_vehicles-inspection_days-3', 'undo_11603_bak_vehicles-time_periods-3', 'undo_11603_bak_vehicles-preview_site-3', 'undo_11603_bak_vehicles-the_doors-3', 'undo_11603_bak_vehicles-the_weight-3', 'undo_11603_bak_vehicles-input_time-3', 'undo_11603_bak_vehicles-inspection_report_media-3', 3, 3000.00, '2026-01-03 09:00:00', 'undo_11603_bak_vehicles-payment_method-3', 'undo_11603_bak_vehicles-transaction_ref-3', 'fixtures/undo_11603_bak_vehicles/3.jpg', 3, '2026-01-03 09:00:00', 'test', 'fixtures/undo_11603_bak_vehicles/3.jpg', 'test', 'test', 'test');

INSERT INTO `user_auctions` (`id`, `user_id`, `auction_id`, `status`, `created_at`) VALUES
(1, 1, 1, 'active', '2026-01-01 09:00:00'),
(2, 2, 2, 'active', '2026-01-02 09:00:00'),
(3, 3, 3, 'active', '2026-01-03 09:00:00');

INSERT INTO `user_card_permissions` (`id`, `user_id`, `card_key`, `allowed`) VALUES
(1, 1, 'user_card_permissions-card_key-1', 0),
(2, 2, 'user_card_permissions-card_key-2', 0),
(3, 3, 'user_card_permissions-card_key-3', 0);

INSERT INTO `user_tokens` (`id`, `token`) VALUES
(1, 'NOT-A-REAL-SECRET-1'),
(2, 'NOT-A-REAL-SECRET-2'),
(3, 'NOT-A-REAL-SECRET-3');

INSERT INTO `userss_bak_20260820_154444_jawad` (`id`, `phone`, `verification_code`, `failed_attempts`, `last_attempt_time`, `block_status`, `code_expiry`, `identity_type`, `identity_number`, `type_of_account`, `tax_image`, `birth_date`, `arabic_name`, `cr_number`, `english_name`, `gender`, `email`, `identity_image`, `total_insurance_paid`, `purchases_balance`, `wallet`, `id_customer`, `active_auctions_count`, `password`, `last_resend_time`, `created_at`, `iban_account`, `commerce_image`, `company_image`, `national_address_image`, `passport_image`, `country`, `plot_number`, `blocked_until`, `id_package`, `address`, `zip`, `building_no`, `vat_number`, `street`, `district`, `state`, `profile_image`, `city`, `player_id`, `additional_no`, `fcm_token`, `session_token`, `mobile_verified`, `remember_token_hash`, `remember_token_expires_at`) VALUES
(1, '966500000001', '1111', 1, '2026-01-01 09:00:00', 'allowed', '2026-01-01 09:00:00', 'id', '1000000001', 'personal', 'fixtures/userss_bak_20260820_154444_jawad/1.jpg', '2026-01-01', 'تجريبي 1 — userss_bak_20260820_154444_jawad', '1010000001', 'تجريبي 1 — userss_bak_20260820_154444_jawad', 'male', 'test1@example.invalid', 'fixtures/userss_bak_20260820_154444_jawad/1.jpg', 1000.00, 1000.00, 1000.00, 'userss_bak_20260820_154444_jawad-id_customer-1', 1, 'NOT-A-REAL-SECRET-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'SA0000000000000000000001', 'fixtures/userss_bak_20260820_154444_jawad/1.jpg', 'fixtures/userss_bak_20260820_154444_jawad/1.jpg', 'fixtures/userss_bak_20260820_154444_jawad/1.jpg', 'fixtures/userss_bak_20260820_154444_jawad/1.jpg', 'userss_bak_20260820_154444_jawad-country-1', 'userss_bak_20260820_154444_jawad-plot_number-1', '2026-01-01 09:00:00', 1, 'userss_bak_20260820_154444_jawad-address-1', 'userss_bak_20260820_', 'userss_bak_20260820_', '300000000000001', 'userss_bak_20260820_154444_jawad-street-1', 'userss_bak_20260820_154444_jawad-district-1', 'test', 'fixtures/userss_bak_20260820_154444_jawad/1.jpg', 'userss_bak_20260820_154444_jawad-city-1', 'userss_bak_20260820_154444_jawad-player_id-1', 'userss_bak', 'NOT-A-REAL-SECRET-1', 'NOT-A-REAL-SECRET-1', 0, 'NOT-A-REAL-SECRET-1', '2026-01-01 09:00:00'),
(2, '966500000002', '2222', 2, '2026-01-02 09:00:00', 'allowed', '2026-01-02 09:00:00', 'id', '1000000002', 'personal', 'fixtures/userss_bak_20260820_154444_jawad/2.jpg', '2026-01-02', 'تجريبي 2 — userss_bak_20260820_154444_jawad', '1010000002', 'تجريبي 2 — userss_bak_20260820_154444_jawad', 'male', 'test2@example.invalid', 'fixtures/userss_bak_20260820_154444_jawad/2.jpg', 2000.00, 2000.00, 2000.00, 'userss_bak_20260820_154444_jawad-id_customer-2', 2, 'NOT-A-REAL-SECRET-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'SA0000000000000000000002', 'fixtures/userss_bak_20260820_154444_jawad/2.jpg', 'fixtures/userss_bak_20260820_154444_jawad/2.jpg', 'fixtures/userss_bak_20260820_154444_jawad/2.jpg', 'fixtures/userss_bak_20260820_154444_jawad/2.jpg', 'userss_bak_20260820_154444_jawad-country-2', 'userss_bak_20260820_154444_jawad-plot_number-2', '2026-01-02 09:00:00', 2, 'userss_bak_20260820_154444_jawad-address-2', 'userss_bak_20260820_', 'userss_bak_20260820_', '300000000000002', 'userss_bak_20260820_154444_jawad-street-2', 'userss_bak_20260820_154444_jawad-district-2', 'test', 'fixtures/userss_bak_20260820_154444_jawad/2.jpg', 'userss_bak_20260820_154444_jawad-city-2', 'userss_bak_20260820_154444_jawad-player_id-2', 'userss_bak', 'NOT-A-REAL-SECRET-2', 'NOT-A-REAL-SECRET-2', 0, 'NOT-A-REAL-SECRET-2', '2026-01-02 09:00:00'),
(3, '966500000003', '3333', 3, '2026-01-03 09:00:00', 'allowed', '2026-01-03 09:00:00', 'id', '1000000003', 'personal', 'fixtures/userss_bak_20260820_154444_jawad/3.jpg', '2026-01-03', 'تجريبي 3 — userss_bak_20260820_154444_jawad', '1010000003', 'تجريبي 3 — userss_bak_20260820_154444_jawad', 'male', 'test3@example.invalid', 'fixtures/userss_bak_20260820_154444_jawad/3.jpg', 3000.00, 3000.00, 3000.00, 'userss_bak_20260820_154444_jawad-id_customer-3', 3, 'NOT-A-REAL-SECRET-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'SA0000000000000000000003', 'fixtures/userss_bak_20260820_154444_jawad/3.jpg', 'fixtures/userss_bak_20260820_154444_jawad/3.jpg', 'fixtures/userss_bak_20260820_154444_jawad/3.jpg', 'fixtures/userss_bak_20260820_154444_jawad/3.jpg', 'userss_bak_20260820_154444_jawad-country-3', 'userss_bak_20260820_154444_jawad-plot_number-3', '2026-01-03 09:00:00', 3, 'userss_bak_20260820_154444_jawad-address-3', 'userss_bak_20260820_', 'userss_bak_20260820_', '300000000000003', 'userss_bak_20260820_154444_jawad-street-3', 'userss_bak_20260820_154444_jawad-district-3', 'test', 'fixtures/userss_bak_20260820_154444_jawad/3.jpg', 'userss_bak_20260820_154444_jawad-city-3', 'userss_bak_20260820_154444_jawad-player_id-3', 'userss_bak', 'NOT-A-REAL-SECRET-3', 'NOT-A-REAL-SECRET-3', 0, 'NOT-A-REAL-SECRET-3', '2026-01-03 09:00:00');

INSERT INTO `vehicle_exits` (`id`, `vehicle_id`, `auction_id`, `invoice_id`, `buyer_user_id`, `recipient_name`, `recipient_id`, `recipient_phone`, `recipient_id_image`, `exit_type`, `exit_reason`, `transfer_status`, `barcode`, `declaration_file`, `transfer_proof_file`, `stage`, `warehouse_exit_at`, `transfer_at`, `notes`, `created_by`, `created_at`, `updated_at`, `manager_alerted_at`, `owner_alerted_at`, `declaration_date`, `ban_lifted_at`) VALUES
(1, 1, 1, 'vehicle_exits-invoice_id-1', 1, 'تجريبي 1 — vehicle_exits', 'vehicle_exits-recipient_id-1', '966500000001', 'fixtures/vehicle_exits/1.jpg', 'after_transfer', 'no_plates_no_inspection', 'pending', 'NOT-A-REAL-SECRET-1', 'vehicle_exits-declaration_file-1', 'vehicle_exits-transfer_proof_file-1', 'created', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (vehicle_exits)', 'vehicle_exits-created_by-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01', '2026-01-01 09:00:00'),
(2, 2, 2, 'vehicle_exits-invoice_id-2', 2, 'تجريبي 2 — vehicle_exits', 'vehicle_exits-recipient_id-2', '966500000002', 'fixtures/vehicle_exits/2.jpg', 'after_transfer', 'no_plates_no_inspection', 'pending', 'NOT-A-REAL-SECRET-2', 'vehicle_exits-declaration_file-2', 'vehicle_exits-transfer_proof_file-2', 'created', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (vehicle_exits)', 'vehicle_exits-created_by-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02', '2026-01-02 09:00:00'),
(3, 3, 3, 'vehicle_exits-invoice_id-3', 3, 'تجريبي 3 — vehicle_exits', 'vehicle_exits-recipient_id-3', '966500000003', 'fixtures/vehicle_exits/3.jpg', 'after_transfer', 'no_plates_no_inspection', 'pending', 'NOT-A-REAL-SECRET-3', 'vehicle_exits-declaration_file-3', 'vehicle_exits-transfer_proof_file-3', 'created', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (vehicle_exits)', 'vehicle_exits-created_by-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03', '2026-01-03 09:00:00');

INSERT INTO `vehicle_exits_bak_20260716_145551` (`id`, `vehicle_id`, `auction_id`, `invoice_id`, `buyer_user_id`, `recipient_name`, `recipient_id`, `recipient_phone`, `recipient_id_image`, `exit_type`, `exit_reason`, `transfer_status`, `barcode`, `declaration_file`, `transfer_proof_file`, `stage`, `warehouse_exit_at`, `transfer_at`, `notes`, `created_by`, `created_at`, `updated_at`, `manager_alerted_at`, `owner_alerted_at`) VALUES
(1, 1, 1, 'vehicle_exits_bak_20260716_145551-invoice_id-1', 1, 'تجريبي 1 — vehicle_exits_bak_20260716_145551', 'vehicle_exits_bak_20260716_145551-recipient_id-1', '966500000001', 'fixtures/vehicle_exits_bak_20260716_145551/1.jpg', 'after_transfer', 'no_plates_no_inspection', 'pending', 'NOT-A-REAL-SECRET-1', 'vehicle_exits_bak_20260716_145551-declaration_file-1', 'vehicle_exits_bak_20260716_145551-transfer_proof_file-1', 'created', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (vehicle_exits_bak_20260716_145551)', 'vehicle_exits_bak_20260716_145551-created_by-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 2, 2, 'vehicle_exits_bak_20260716_145551-invoice_id-2', 2, 'تجريبي 2 — vehicle_exits_bak_20260716_145551', 'vehicle_exits_bak_20260716_145551-recipient_id-2', '966500000002', 'fixtures/vehicle_exits_bak_20260716_145551/2.jpg', 'after_transfer', 'no_plates_no_inspection', 'pending', 'NOT-A-REAL-SECRET-2', 'vehicle_exits_bak_20260716_145551-declaration_file-2', 'vehicle_exits_bak_20260716_145551-transfer_proof_file-2', 'created', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (vehicle_exits_bak_20260716_145551)', 'vehicle_exits_bak_20260716_145551-created_by-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 3, 3, 'vehicle_exits_bak_20260716_145551-invoice_id-3', 3, 'تجريبي 3 — vehicle_exits_bak_20260716_145551', 'vehicle_exits_bak_20260716_145551-recipient_id-3', '966500000003', 'fixtures/vehicle_exits_bak_20260716_145551/3.jpg', 'after_transfer', 'no_plates_no_inspection', 'pending', 'NOT-A-REAL-SECRET-3', 'vehicle_exits_bak_20260716_145551-declaration_file-3', 'vehicle_exits_bak_20260716_145551-transfer_proof_file-3', 'created', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (vehicle_exits_bak_20260716_145551)', 'vehicle_exits_bak_20260716_145551-created_by-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `vehicle_images` (`id`, `vehicle_id`, `image_path`, `image_url`, `sort_order`, `storage_disk`, `is_primary`, `created_at`, `image_blob`, `image_mime`) VALUES
(1, 1, 'fixtures/vehicle_images/1.jpg', 'fixtures/vehicle_images/1.jpg', 1, 'vehicle_images-storage_disk-1', 0, '2026-01-01 09:00:00', NULL, 'fixtures/vehicle_images/1.jpg'),
(2, 2, 'fixtures/vehicle_images/2.jpg', 'fixtures/vehicle_images/2.jpg', 2, 'vehicle_images-storage_disk-2', 0, '2026-01-02 09:00:00', NULL, 'fixtures/vehicle_images/2.jpg'),
(3, 3, 'fixtures/vehicle_images/3.jpg', 'fixtures/vehicle_images/3.jpg', 3, 'vehicle_images-storage_disk-3', 0, '2026-01-03 09:00:00', NULL, 'fixtures/vehicle_images/3.jpg');

INSERT INTO `vehicle_receipt` (`id`, `date_received`, `recipient_name`, `image_path`, `id_number`, `vehicle_type`, `model`, `color`, `plate_number`, `chassis_number`, `phone_number`, `created_at`) VALUES
(1, '2026-01-01 09:00:00', 'تجريبي 1 — vehicle_receipt', 'fixtures/vehicle_receipt/1.jpg', 'vehicle_receipt-id_number-1', 'test', 'vehicle_receipt-model-1', 'vehicle_receipt-color-1', 'vehicle_receipt-plate_number-1', 'vehicle_receipt-chassis_number-1', '966500000001', '2026-01-01 09:00:00'),
(2, '2026-01-02 09:00:00', 'تجريبي 2 — vehicle_receipt', 'fixtures/vehicle_receipt/2.jpg', 'vehicle_receipt-id_number-2', 'test', 'vehicle_receipt-model-2', 'vehicle_receipt-color-2', 'vehicle_receipt-plate_number-2', 'vehicle_receipt-chassis_number-2', '966500000002', '2026-01-02 09:00:00'),
(3, '2026-01-03 09:00:00', 'تجريبي 3 — vehicle_receipt', 'fixtures/vehicle_receipt/3.jpg', 'vehicle_receipt-id_number-3', 'test', 'vehicle_receipt-model-3', 'vehicle_receipt-color-3', 'vehicle_receipt-plate_number-3', 'vehicle_receipt-chassis_number-3', '966500000003', '2026-01-03 09:00:00');

INSERT INTO `vehicles` (`id`, `name`, `color`, `mileage`, `year`, `price`, `created_at`) VALUES
(1, 'تجريبي 1 — vehicles', 'vehicles-color-1', 'vehicles-mileage-1', 'vehicles-y', 'vehicles-price-1', '2026-01-01 09:00:00'),
(2, 'تجريبي 2 — vehicles', 'vehicles-color-2', 'vehicles-mileage-2', 'vehicles-y', 'vehicles-price-2', '2026-01-02 09:00:00'),
(3, 'تجريبي 3 — vehicles', 'vehicles-color-3', 'vehicles-mileage-3', 'vehicles-y', 'vehicles-price-3', '2026-01-03 09:00:00');

INSERT INTO `waiver_requests` (`id`, `date_received`, `recipient_name`, `owner_name`, `image_path`, `id_number`, `vehicle_type`, `model`, `color`, `plate_number`, `chassis_number`, `phone_number`, `created_at`, `request_type`, `status`, `status_note`, `progress_step`) VALUES
(1, '2026-01-01', 'تجريبي 1 — waiver_requests', 'تجريبي 1 — waiver_requests', 'fixtures/waiver_requests/1.jpg', 'waiver_requests-id_number-1', 'test', 'waiver_requests-model-1', 'waiver_requests-color-1', 'waiver_requests-plate_number-1', 'waiver_requests-chassis_number-1', '966500000001', '2026-01-01 09:00:00', 'test', 'test', 'بيانات اختبار مُصطنَعة (waiver_requests)', 'waiver_requests-progress_step-1'),
(2, '2026-01-02', 'تجريبي 2 — waiver_requests', 'تجريبي 2 — waiver_requests', 'fixtures/waiver_requests/2.jpg', 'waiver_requests-id_number-2', 'test', 'waiver_requests-model-2', 'waiver_requests-color-2', 'waiver_requests-plate_number-2', 'waiver_requests-chassis_number-2', '966500000002', '2026-01-02 09:00:00', 'test', 'test', 'بيانات اختبار مُصطنَعة (waiver_requests)', 'waiver_requests-progress_step-2'),
(3, '2026-01-03', 'تجريبي 3 — waiver_requests', 'تجريبي 3 — waiver_requests', 'fixtures/waiver_requests/3.jpg', 'waiver_requests-id_number-3', 'test', 'waiver_requests-model-3', 'waiver_requests-color-3', 'waiver_requests-plate_number-3', 'waiver_requests-chassis_number-3', '966500000003', '2026-01-03 09:00:00', 'test', 'test', 'بيانات اختبار مُصطنَعة (waiver_requests)', 'waiver_requests-progress_step-3');

INSERT INTO `wallet_health_findings` (`id`, `code`, `subject`, `severity`, `title`, `detail`, `amount`, `status`, `acknowledged_by`, `acknowledged_at`, `first_seen_at`, `last_seen_at`, `resolved_at`) VALUES
(1, 'NOT-A-REAL-SECRET-1', 'wallet_health_findings-subject-1', 'wallet_hea', 'تجريبي 1 — wallet_health_findings', 'wallet_health_findings-detail-1', 1000.00, 'test', 1, '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
(2, 'NOT-A-REAL-SECRET-2', 'wallet_health_findings-subject-2', 'wallet_hea', 'تجريبي 2 — wallet_health_findings', 'wallet_health_findings-detail-2', 2000.00, 'test', 2, '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00'),
(3, 'NOT-A-REAL-SECRET-3', 'wallet_health_findings-subject-3', 'wallet_hea', 'تجريبي 3 — wallet_health_findings', 'wallet_health_findings-detail-3', 3000.00, 'test', 3, '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00');

INSERT INTO `wallet_logs` (`id`, `user_id`, `amount`, `added_by`, `created_at`) VALUES
(1, 1, 1000.00, 'wallet_logs-added_by-1', '2026-01-01 09:00:00'),
(2, 2, 2000.00, 'wallet_logs-added_by-2', '2026-01-02 09:00:00'),
(3, 3, 3000.00, 'wallet_logs-added_by-3', '2026-01-03 09:00:00');

INSERT INTO `wallet_transactions` (`id`, `user_id`, `type`, `category`, `amount`, `odoo_reference`, `odoo_payment_id`, `transfer_request_id`, `note`, `created_at`) VALUES
(1, 1, 'test', 'wallet_transactions-category-1', 1000.00, 'wallet_transactions-odoo_reference-1', 'wallet_transactions-odoo_payment_id-1', 1, 'بيانات اختبار مُصطنَعة (wallet_transactions)', '2026-01-01 09:00:00'),
(2, 2, 'test', 'wallet_transactions-category-2', 2000.00, 'wallet_transactions-odoo_reference-2', 'wallet_transactions-odoo_payment_id-2', 2, 'بيانات اختبار مُصطنَعة (wallet_transactions)', '2026-01-02 09:00:00'),
(3, 3, 'test', 'wallet_transactions-category-3', 3000.00, 'wallet_transactions-odoo_reference-3', 'wallet_transactions-odoo_payment_id-3', 3, 'بيانات اختبار مُصطنَعة (wallet_transactions)', '2026-01-03 09:00:00');

INSERT INTO `webhook_failures` (`id`, `endpoint`, `method`, `http_status`, `message`, `detail`, `request_body`, `response_body`, `remote_ip`, `created_at`) VALUES
(1, 'webhook_failures-endpoint-1', 'webhook_fa', 1, 'بيانات اختبار مُصطنَعة (webhook_failures)', 'webhook_failures-detail-1', 'webhook_failures-request_body-1', 'webhook_failures-response_body-1', 'webhook_failures-remote_ip-1', '2026-01-01 09:00:00'),
(2, 'webhook_failures-endpoint-2', 'webhook_fa', 2, 'بيانات اختبار مُصطنَعة (webhook_failures)', 'webhook_failures-detail-2', 'webhook_failures-request_body-2', 'webhook_failures-response_body-2', 'webhook_failures-remote_ip-2', '2026-01-02 09:00:00'),
(3, 'webhook_failures-endpoint-3', 'webhook_fa', 3, 'بيانات اختبار مُصطنَعة (webhook_failures)', 'webhook_failures-detail-3', 'webhook_failures-request_body-3', 'webhook_failures-response_body-3', 'webhook_failures-remote_ip-3', '2026-01-03 09:00:00');

INSERT INTO `zaar_20260805_bak` (`id`, `user_id`, `amount`, `status`, `odoo_payment_id`, `linked_auction_id`, `linked_invoice_id`, `created_at`, `held_at`, `locked_at`, `refunded_at`, `confiscated_at`, `notes`) VALUES
(1, 1, 1000.00, 'test', 'zaar_20260805_bak-odoo_payment_id-1', 1, 'zaar_20260805_bak-linked_invoice_id-1', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-01-01 09:00:00', 'بيانات اختبار مُصطنَعة (zaar_20260805_bak)'),
(2, 2, 2000.00, 'test', 'zaar_20260805_bak-odoo_payment_id-2', 2, 'zaar_20260805_bak-linked_invoice_id-2', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', '2026-01-02 09:00:00', 'بيانات اختبار مُصطنَعة (zaar_20260805_bak)'),
(3, 3, 3000.00, 'test', 'zaar_20260805_bak-odoo_payment_id-3', 3, 'zaar_20260805_bak-linked_invoice_id-3', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-01-03 09:00:00', 'بيانات اختبار مُصطنَعة (zaar_20260805_bak)');

SET FOREIGN_KEY_CHECKS=1;
