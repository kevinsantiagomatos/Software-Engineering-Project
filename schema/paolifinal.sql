-- MySQL dump 10.13  Distrib 8.0.40, for macos14 (arm64)
--
-- Host: 127.0.0.1    Database: palogroup
-- ------------------------------------------------------
-- Server version	9.3.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `audit_log`
--

DROP TABLE IF EXISTS `audit_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_log` (
  `id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `action` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `actor` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `detail` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `timestamp` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `audit_log_chk_1` CHECK (json_valid(`detail`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `audit_log`
--

LOCK TABLES `audit_log` WRITE;
/*!40000 ALTER TABLE `audit_log` DISABLE KEYS */;
INSERT INTO `audit_log` VALUES ('03b9f86ff4329ce0','doc_status','reviewer_hr@example.com','{\"doc_id\": \"5a3ddcd008265dc2fb4a4b7a\", \"status\": \"approved\"}','2026-03-09 13:32:08.000000'),('065715d5e219fdc7','policy_definition_delete','compliance.admin@paoli.local','{\"policy_id\": \"qa_temp_policy\", \"label\": \"QA Temp Policy\"}','2026-05-19 20:52:24.000000'),('070ef1029d2c91d9','it_access_configure','email2@gmail.com','{\"email\": \"testuser2@gmail.com\", \"access_key\": \"m365_account\", \"state\": \"configured_pending_confirmation\"}','2026-05-19 18:53:16.000000'),('0c7b576d55dc549b','training_complete','testuser2@gmail.com','{\"module_id\": \"tools\"}','2026-05-18 13:55:55.000000'),('0d17cb8502922715','doc_status','hr@paoli.local','{\"doc_id\": \"0f5b7b3c99fee3cc201952bb\", \"status\": \"approved\"}','2026-04-17 21:20:01.000000'),('0d76f03e33063a17','it_access_configure','email2@gmail.com','{\"email\": \"testuser2@gmail.com\", \"access_key\": \"slack_access\", \"state\": \"configured_pending_confirmation\"}','2026-05-18 13:13:00.000000'),('0f40d2694c20c077','hire_register','hr@paoli.local','{\"hire_id\": \"ac0541c6076f1907\", \"email\": \"paolihr@paoli.com\", \"role\": \"employee\"}','2026-04-17 20:52:02.000000'),('173ac812e0c08d42','it_access_response','testuser2@gmail.com','{\"email\": \"testuser2@gmail.com\", \"access_key\": \"slack_access\", \"response\": \"confirmed\"}','2026-05-18 13:14:07.000000'),('2f0ec2ea5f8d6d33','compliance_check_update','compliance.admin@paoli.local','{\"email\": \"testuser2@gmail.com\", \"check_key\": \"policy_review\", \"state\": \"approved\", \"note\": \"\"}','2026-05-18 13:59:41.000000'),('351e63f7bc9b07b6','training_complete','testuser2@gmail.com','{\"module_id\": \"handbook\"}','2026-05-18 13:55:54.000000'),('3a78f7409d935abd','policy_definition_state','compliance.admin@paoli.local','{\"policy_id\": \"company_policies\", \"is_active\": true}','2026-05-19 20:38:21.000000'),('463445aac359ebd9','doc_status','reviewer_hr@example.com','{\"doc_id\": \"5ddadf8b62139224137de307\", \"status\": \"approved\"}','2026-03-09 13:32:08.000000'),('472f73628d91d9e0','policy_definition_state','compliance.admin@paoli.local','{\"policy_id\": \"company_policies\", \"is_active\": false}','2026-05-19 20:38:21.000000'),('47b78342b7ea40c9','policy_ack','testuser2@gmail.com','{\"policy_id\": \"billing_manual\"}','2026-05-18 13:39:35.000000'),('4d4ae9ecbef2aaea','doc_status','reviewer_hr@example.com','{\"doc_id\": \"f3782a3e125ef6853283a14b\", \"status\": \"approved\"}','2026-03-09 13:32:16.000000'),('4ef99e912b28f318','compliance_check_update','compliance.admin@paoli.local','{\"email\": \"testuser2@gmail.com\", \"check_key\": \"contracts_review\", \"state\": \"approved\", \"note\": \"\"}','2026-05-18 13:59:44.000000'),('4f2498eca03a283b','doc_status','reviewer_hr@example.com','{\"doc_id\": \"005196cc2cff08fc5b4cbd38\", \"status\": \"approved\"}','2026-03-09 13:32:01.000000'),('5123f00cf46dd124','it_access_configure','email2@gmail.com','{\"email\": \"testuser2@gmail.com\", \"access_key\": \"client_access\", \"state\": \"configured_pending_confirmation\"}','2026-05-18 13:13:12.000000'),('5366452a51c26e37','doc_status','reviewer_hr@example.com','{\"doc_id\": \"0adeb07e050fb08843ee88fc\", \"status\": \"approved\"}','2026-03-09 13:32:06.000000'),('5de9b4ecdaecc6bd','it_access_configure','email2@gmail.com','{\"email\": \"testuser2@gmail.com\", \"access_key\": \"m365_account\", \"state\": \"configured_pending_confirmation\"}','2026-05-18 13:12:13.000000'),('649060632c29c192','it_access_response','testuser2@gmail.com','{\"email\": \"testuser2@gmail.com\", \"access_key\": \"client_access\", \"response\": \"confirmed\"}','2026-05-18 13:14:12.000000'),('6d17519d6ad9497e','doc_status','hr.admin@paoli.local','{\"doc_id\": \"585e9eefdd15d9d9cb1239a1\", \"status\": \"pending_review\"}','2026-05-19 16:29:37.000000'),('6f3efc8b6428ca72','doc_status','reviewer_hr@example.com','{\"doc_id\": \"dfde879abb881b20aa87e6cc\", \"status\": \"rejected\"}','2026-04-17 12:59:06.000000'),('726738ca6d498665','doc_status','hr.admin@paoli.local','{\"doc_id\": \"0adeb07e050fb08843ee88fc\", \"status\": \"rejected\"}','2026-05-19 16:29:34.000000'),('7f413d83ae6c695a','doc_status','reviewer_hr@example.com','{\"doc_id\": \"6cf17f59d912e48b4092352b\", \"status\": \"approved\"}','2026-03-09 13:32:09.000000'),('83ea968f926f51e9','it_access_configure','email2@gmail.com','{\"email\": \"testuser2@gmail.com\", \"access_key\": \"quickbooks_time\", \"state\": \"configured_pending_confirmation\"}','2026-05-18 13:12:54.000000'),('919e5c5372da9d9f','it_access_configure','email2@gmail.com','{\"email\": \"testuser2@gmail.com\", \"access_key\": \"atlassian_access\", \"state\": \"configured_pending_confirmation\"}','2026-05-18 13:13:05.000000'),('926d9b398187915a','policy_ack','testuser2@gmail.com','{\"policy_id\": \"billing_manual\"}','2026-05-18 13:15:50.000000'),('92df81466201c0a9','compliance_check_update','compliance.admin@paoli.local','{\"email\": \"testuser2@gmail.com\", \"check_key\": \"final_signoff\", \"state\": \"approved\", \"note\": \"\"}','2026-05-18 13:59:46.000000'),('9318de7c098795be','policy_definition_create','compliance.admin@paoli.local','{\"policy_id\": \"qa_temp_policy\", \"label\": \"QA Temp Policy\", \"file_path\": \"policies/qa_temp_policy.pdf\"}','2026-05-19 20:52:24.000000'),('949bf88d085c26f8','doc_status','hr.admin@paoli.local','{\"doc_id\": \"0adeb07e050fb08843ee88fc\", \"status\": \"pending_review\"}','2026-05-19 16:29:28.000000'),('97e112cf24926f4a','it_access_configure','email2@gmail.com','{\"email\": \"testuser2@gmail.com\", \"access_key\": \"laptop_intune\", \"state\": \"configured_pending_confirmation\"}','2026-05-18 13:12:07.000000'),('999cd0c5e83278ad','doc_status','reviewer_hr@example.com','{\"doc_id\": \"e9d3d3a2bbf785529d608191\", \"status\": \"approved\"}','2026-03-09 13:32:14.000000'),('9a2daf3d9c33ae8c','it_access_configure','email2@gmail.com','{\"email\": \"testuser2@gmail.com\", \"access_key\": \"quickbooks_time\", \"state\": \"not_configured\"}','2026-05-18 13:12:47.000000'),('a0dcb2ff2732c1cb','training_complete','testuser2@gmail.com','{\"module_id\": \"security101\"}','2026-05-18 13:55:55.000000'),('a3c327562a153f45','compliance_check_update','compliance.admin@paoli.local','{\"email\": \"testuser2@gmail.com\", \"check_key\": \"final_signoff\", \"state\": \"pending_review\", \"note\": \"\"}','2026-05-19 19:11:02.000000'),('bee5899c537a98d0','it_access_response','testuser2@gmail.com','{\"email\": \"testuser2@gmail.com\", \"access_key\": \"quickbooks_time\", \"response\": \"confirmed\"}','2026-05-18 13:14:05.000000'),('c38727ead0989150','doc_status','reviewer_hr@example.com','{\"doc_id\": \"8b86a138c96fb34fd2b23129\", \"status\": \"approved\"}','2026-03-09 13:32:11.000000'),('c7b60349d3e0be0c','it_access_configure','email2@gmail.com','{\"email\": \"testuser2@gmail.com\", \"access_key\": \"laptop_intune\", \"state\": \"not_configured\"}','2026-05-19 18:53:06.000000'),('c7e5d853ebde5a9d','doc_status','reviewer_hr@example.com','{\"doc_id\": \"585e9eefdd15d9d9cb1239a1\", \"status\": \"approved\"}','2026-03-09 13:32:07.000000'),('c92c85e387ac80c4','compliance_check_update','compliance.admin@paoli.local','{\"email\": \"testuser2@gmail.com\", \"check_key\": \"documents_review\", \"state\": \"approved\", \"note\": \"\"}','2026-05-18 13:59:39.000000'),('cc140923ad298ea1','it_access_response','testuser2@gmail.com','{\"email\": \"testuser2@gmail.com\", \"access_key\": \"laptop_intune\", \"response\": \"confirmed\"}','2026-05-18 13:14:00.000000'),('d0aa816b3e873cf3','hire_update','hr.admin@paoli.local','{\"hire_id\": \"aef22b9569b34a8f\", \"email\": \"testuser2@gmail.com\", \"updated_fields\": [\"first_name\", \"middle_name\", \"last_name\", \"phone\", \"gov_id\", \"street\", \"city\", \"state\", \"postal_code\", \"country\", \"department\", \"manager\", \"status\", \"employment_type\", \"dob\", \"start_date\"]}','2026-04-18 14:59:28.000000'),('d19b7319cd98e5a2','doc_status','reviewer_hr@example.com','{\"doc_id\": \"9a2f490ce25ec0d9da185b64\", \"status\": \"approved\"}','2026-03-09 13:32:12.000000'),('dfebe105e46af9d7','doc_status','reviewer_hr@example.com','{\"doc_id\": \"e464f8fbb0335edc6173e0a9\", \"status\": \"approved\"}','2026-03-09 13:32:13.000000'),('e7541a23da04b6e7','doc_status','reviewer_hr@example.com','{\"doc_id\": \"6e2b632d21b330f2293b4cc2\", \"status\": \"approved\"}','2026-03-09 13:32:10.000000'),('ed62d92331a32b4d','it_access_response','testuser2@gmail.com','{\"email\": \"testuser2@gmail.com\", \"access_key\": \"atlassian_access\", \"response\": \"confirmed\"}','2026-05-18 13:14:10.000000'),('fce46021099ed172','it_access_response','testuser2@gmail.com','{\"email\": \"testuser2@gmail.com\", \"access_key\": \"m365_account\", \"response\": \"confirmed\"}','2026-05-18 13:14:03.000000');
/*!40000 ALTER TABLE `audit_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `compliance_review_item`
--

DROP TABLE IF EXISTS `compliance_review_item`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `compliance_review_item` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `check_key` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `check_label` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `state` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending_review',
  `reviewer_note` text COLLATE utf8mb4_unicode_ci,
  `reviewed_by` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reviewed_at` datetime(6) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  `updated_by` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_compliance_email_key` (`email`,`check_key`),
  KEY `idx_compliance_email_state` (`email`,`state`),
  KEY `idx_compliance_email_updated` (`email`,`updated_at`)
) ENGINE=InnoDB AUTO_INCREMENT=233 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `compliance_review_item`
--

LOCK TABLES `compliance_review_item` WRITE;
/*!40000 ALTER TABLE `compliance_review_item` DISABLE KEYS */;
INSERT INTO `compliance_review_item` VALUES (1,'testuser2@gmail.com','documents_review','Required documents reviewed and validated','approved',NULL,'compliance.admin@paoli.local','2026-05-18 13:59:39.423737','2026-05-18 13:07:59.557661','2026-05-18 13:59:39.423737','compliance.admin@paoli.local'),(2,'testuser2@gmail.com','policy_review','Policy acknowledgments verified','approved',NULL,'compliance.admin@paoli.local','2026-05-18 13:59:41.988585','2026-05-18 13:07:59.568129','2026-05-18 13:59:41.988585','compliance.admin@paoli.local'),(3,'testuser2@gmail.com','contracts_review','Contract and certifications reviewed','approved',NULL,'compliance.admin@paoli.local','2026-05-18 13:59:44.071005','2026-05-18 13:07:59.570480','2026-05-18 13:59:44.071005','compliance.admin@paoli.local'),(4,'testuser2@gmail.com','final_signoff','Final compliance sign-off','pending_review',NULL,NULL,NULL,'2026-05-18 13:07:59.575135','2026-05-19 19:11:02.091212','compliance.admin@paoli.local');
/*!40000 ALTER TABLE `compliance_review_item` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `department`
--

DROP TABLE IF EXISTS `department`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `department` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_department_name` (`name`),
  KEY `idx_department_active` (`is_active`)
) ENGINE=InnoDB AUTO_INCREMENT=56 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `department`
--

LOCK TABLES `department` WRITE;
/*!40000 ALTER TABLE `department` DISABLE KEYS */;
INSERT INTO `department` VALUES (1,'Operations',1,'2026-04-18 19:07:47.766200'),(2,'HR',1,'2026-04-18 19:07:47.766200'),(3,'IT',1,'2026-04-18 19:07:47.766200'),(4,'Compliance',1,'2026-04-18 19:07:47.766200'),(5,'Management',1,'2026-04-18 19:07:47.766200');
/*!40000 ALTER TABLE `department` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `document`
--

DROP TABLE IF EXISTS `document`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `document` (
  `id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `original_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stored_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `uploader_email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `uploader_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT 'pending_review',
  `size_bytes` bigint DEFAULT NULL,
  `checksum_sha256` char(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `uploaded_at` datetime(6) DEFAULT NULL,
  `doc_type` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_doc_email` (`uploader_email`),
  KEY `idx_doc_type` (`doc_type`),
  KEY `idx_doc_status` (`status`),
  KEY `idx_doc_uploaded_at` (`uploaded_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `document`
--

LOCK TABLES `document` WRITE;
/*!40000 ALTER TABLE `document` DISABLE KEYS */;
INSERT INTO `document` VALUES ('005196cc2cff08fc5b4cbd38','istockphoto-898916122-612x612.jpg','005196cc2cff08fc5b4cbd38_istockphoto-898916122-612x612.jpg','testuser2@gmail.com','Test User','approved',45637,'627081c318b3036e4fb5478180dd27a13fbfc2e8e61cb6b59fd50bbf9d1ac678','2026-03-09 13:04:28.000000','background_check'),('03d61315b0cfaec3376ca82a','istockphoto-898916122-612x612 (1).jpg','03d61315b0cfaec3376ca82a_istockphoto-898916122-612x612_1.jpg','hr@paoli.local','HR Admin','pending_review',45637,'627081c318b3036e4fb5478180dd27a13fbfc2e8e61cb6b59fd50bbf9d1ac678','2026-04-17 21:19:44.000000','government_id'),('0adeb07e050fb08843ee88fc','istockphoto-898916122-612x612.jpg','0adeb07e050fb08843ee88fc_istockphoto-898916122-612x612.jpg','testuser2@gmail.com','Test User','rejected',45637,'627081c318b3036e4fb5478180dd27a13fbfc2e8e61cb6b59fd50bbf9d1ac678','2026-03-09 13:04:28.000000','crim_compliance'),('0f5b7b3c99fee3cc201952bb','istockphoto-898916122-612x612 (1).jpg','0f5b7b3c99fee3cc201952bb_istockphoto-898916122-612x612_1.jpg','hr@paoli.local','HR Admin','approved',45637,'627081c318b3036e4fb5478180dd27a13fbfc2e8e61cb6b59fd50bbf9d1ac678','2026-04-17 21:19:44.000000','w9'),('585e9eefdd15d9d9cb1239a1','istockphoto-898916122-612x612.jpg','585e9eefdd15d9d9cb1239a1_istockphoto-898916122-612x612.jpg','testuser2@gmail.com','Test User','pending_review',45637,'627081c318b3036e4fb5478180dd27a13fbfc2e8e61cb6b59fd50bbf9d1ac678','2026-03-09 13:04:28.000000','signed_contract'),('5a3ddcd008265dc2fb4a4b7a','istockphoto-898916122-612x612.jpg','5a3ddcd008265dc2fb4a4b7a_istockphoto-898916122-612x612.jpg','testuser2@gmail.com','Test User','approved',45637,'627081c318b3036e4fb5478180dd27a13fbfc2e8e61cb6b59fd50bbf9d1ac678','2026-03-09 13:01:31.000000','government_id'),('5ddadf8b62139224137de307','istockphoto-898916122-612x612.jpg','5ddadf8b62139224137de307_istockphoto-898916122-612x612.jpg','testuser2@gmail.com','Test User','approved',45637,'627081c318b3036e4fb5478180dd27a13fbfc2e8e61cb6b59fd50bbf9d1ac678','2026-03-09 13:04:28.000000','comptroller_registry'),('6cf17f59d912e48b4092352b','istockphoto-898916122-612x612.jpg','6cf17f59d912e48b4092352b_istockphoto-898916122-612x612.jpg','testuser2@gmail.com','Test User','approved',45637,'627081c318b3036e4fb5478180dd27a13fbfc2e8e61cb6b59fd50bbf9d1ac678','2026-03-09 13:04:28.000000','policy_ack'),('6e2b632d21b330f2293b4cc2','istockphoto-898916122-612x612.jpg','6e2b632d21b330f2293b4cc2_istockphoto-898916122-612x612.jpg','testuser2@gmail.com','Test User','approved',45637,'627081c318b3036e4fb5478180dd27a13fbfc2e8e61cb6b59fd50bbf9d1ac678','2026-03-09 13:04:28.000000','bank_certification'),('8b86a138c96fb34fd2b23129','istockphoto-898916122-612x612.jpg','8b86a138c96fb34fd2b23129_istockphoto-898916122-612x612.jpg','testuser2@gmail.com','Test User','approved',45637,'627081c318b3036e4fb5478180dd27a13fbfc2e8e61cb6b59fd50bbf9d1ac678','2026-03-09 13:04:28.000000','w9'),('9a2f490ce25ec0d9da185b64','istockphoto-898916122-612x612.jpg','9a2f490ce25ec0d9da185b64_istockphoto-898916122-612x612.jpg','testuser2@gmail.com','Test User','approved',45637,'627081c318b3036e4fb5478180dd27a13fbfc2e8e61cb6b59fd50bbf9d1ac678','2026-03-09 13:04:28.000000','asume_clearance'),('dfde879abb881b20aa87e6cc','istockphoto-898916122-612x612 (1).jpg','dfde879abb881b20aa87e6cc_istockphoto-898916122-612x612_1.jpg','newhire.employee.20260417165100@paoli.local','New Hire Employee','rejected',45637,'627081c318b3036e4fb5478180dd27a13fbfc2e8e61cb6b59fd50bbf9d1ac678','2026-04-17 12:52:20.000000','government_id'),('e464f8fbb0335edc6173e0a9','istockphoto-898916122-612x612.jpg','e464f8fbb0335edc6173e0a9_istockphoto-898916122-612x612.jpg','testuser2@gmail.com','Test User','approved',45637,'627081c318b3036e4fb5478180dd27a13fbfc2e8e61cb6b59fd50bbf9d1ac678','2026-03-09 13:04:28.000000','tax_return'),('e9d3d3a2bbf785529d608191','istockphoto-898916122-612x612.jpg','e9d3d3a2bbf785529d608191_istockphoto-898916122-612x612.jpg','testuser2@gmail.com','Test User','approved',45637,'627081c318b3036e4fb5478180dd27a13fbfc2e8e61cb6b59fd50bbf9d1ac678','2026-03-09 13:04:28.000000','certifications'),('f3782a3e125ef6853283a14b','istockphoto-898916122-612x612.jpg','f3782a3e125ef6853283a14b_istockphoto-898916122-612x612.jpg','testuser2@gmail.com','Test User','approved',45637,'627081c318b3036e4fb5478180dd27a13fbfc2e8e61cb6b59fd50bbf9d1ac678','2026-03-09 13:04:28.000000','resume');
/*!40000 ALTER TABLE `document` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `hire_document_slot`
--

DROP TABLE IF EXISTS `hire_document_slot`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `hire_document_slot` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `hire_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `doc_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `label` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `optional` tinyint(1) NOT NULL DEFAULT '0',
  `created_by` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_hire_doc_slot_type` (`hire_id`,`doc_type`),
  KEY `idx_hire_doc_slot_hire_active` (`hire_id`,`is_active`),
  CONSTRAINT `fk_hire_doc_slot_hire` FOREIGN KEY (`hire_id`) REFERENCES `new_hire` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `hire_document_slot`
--

LOCK TABLES `hire_document_slot` WRITE;
/*!40000 ALTER TABLE `hire_document_slot` DISABLE KEYS */;
/*!40000 ALTER TABLE `hire_document_slot` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `it_access_item`
--

DROP TABLE IF EXISTS `it_access_item`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `it_access_item` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `access_key` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `access_title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `state` varchar(48) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'not_configured',
  `details` text COLLATE utf8mb4_unicode_ci,
  `portal_url` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `username_hint` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  `configured_by` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `configured_at` datetime(6) DEFAULT NULL,
  `hire_response_note` text COLLATE utf8mb4_unicode_ci,
  `hire_response_at` datetime(6) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  `updated_by` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_it_access_email_key` (`email`,`access_key`),
  KEY `idx_it_access_email_state` (`email`,`state`),
  KEY `idx_it_access_email_updated` (`email`,`updated_at`)
) ENGINE=InnoDB AUTO_INCREMENT=178 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `it_access_item`
--

LOCK TABLES `it_access_item` WRITE;
/*!40000 ALTER TABLE `it_access_item` DISABLE KEYS */;
INSERT INTO `it_access_item` VALUES (1,'testuser2@gmail.com','laptop_intune','Configure laptop with Intune and required apps','not_configured',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-05-18 13:08:06.052326','2026-05-19 18:53:06.795841','email2@gmail.com'),(2,'testuser2@gmail.com','m365_account','Create Microsoft 365 account + Out of Office','configured_pending_confirmation',NULL,NULL,NULL,NULL,'email2@gmail.com','2026-05-19 22:53:16.000000',NULL,NULL,'2026-05-18 13:08:06.054664','2026-05-19 18:53:16.037882','email2@gmail.com'),(3,'testuser2@gmail.com','quickbooks_time','Grant QuickBooks Time access (@paoli.io)','configured_confirmed','check spelling','example.com','example@mail',NULL,'email2@gmail.com','2026-05-18 17:12:54.000000',NULL,'2026-05-18 13:14:05.210323','2026-05-18 13:08:06.056446','2026-05-18 13:14:05.210323','testuser2@gmail.com'),(4,'testuser2@gmail.com','slack_access','Add to Slack with SSO','configured_confirmed',NULL,NULL,NULL,NULL,'email2@gmail.com','2026-05-18 17:13:00.000000',NULL,'2026-05-18 13:14:07.873746','2026-05-18 13:08:06.059568','2026-05-18 13:14:07.873746','testuser2@gmail.com'),(5,'testuser2@gmail.com','atlassian_access','Add to Jira & Confluence (SSO)','configured_confirmed',NULL,NULL,NULL,NULL,'email2@gmail.com','2026-05-18 17:13:05.000000',NULL,'2026-05-18 13:14:10.194950','2026-05-18 13:08:06.062429','2026-05-18 13:14:10.194950','testuser2@gmail.com'),(6,'testuser2@gmail.com','client_access','Provision client/project access','configured_confirmed',NULL,NULL,NULL,NULL,'email2@gmail.com','2026-05-18 17:13:11.000000',NULL,'2026-05-18 13:14:12.279052','2026-05-18 13:08:06.065473','2026-05-18 13:14:12.279052','testuser2@gmail.com');
/*!40000 ALTER TABLE `it_access_item` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `it_provision`
--

DROP TABLE IF EXISTS `it_provision`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `it_provision` (
  `id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `items_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `completed_at` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `it_provision_chk_1` CHECK (json_valid(`items_json`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `it_provision`
--

LOCK TABLES `it_provision` WRITE;
/*!40000 ALTER TABLE `it_provision` DISABLE KEYS */;
/*!40000 ALTER TABLE `it_provision` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `job_title`
--

DROP TABLE IF EXISTS `job_title`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `job_title` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `department_id` bigint NOT NULL,
  `name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_job_title_department_name` (`department_id`,`name`),
  KEY `idx_job_title_department` (`department_id`),
  KEY `idx_job_title_active` (`is_active`),
  CONSTRAINT `fk_job_title_department` FOREIGN KEY (`department_id`) REFERENCES `department` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=192 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `job_title`
--

LOCK TABLES `job_title` WRITE;
/*!40000 ALTER TABLE `job_title` DISABLE KEYS */;
INSERT INTO `job_title` VALUES (1,1,'Operations Coordinator',1,'2026-04-18 19:07:47.768918'),(2,1,'Project Coordinator',1,'2026-04-18 19:07:47.768918'),(3,1,'Business Analyst',1,'2026-04-18 19:07:47.768918'),(4,2,'HR Generalist',1,'2026-04-18 19:07:47.768918'),(5,2,'Recruiter',1,'2026-04-18 19:07:47.768918'),(6,2,'HR Coordinator',1,'2026-04-18 19:07:47.768918'),(7,3,'Software Engineer',1,'2026-04-18 19:07:47.768918'),(8,3,'Developer',1,'2026-04-18 19:07:47.768918'),(9,3,'QA Engineer',1,'2026-04-18 19:07:47.768918'),(10,3,'IT Support Specialist',1,'2026-04-18 19:07:47.768918'),(11,4,'Compliance Analyst',1,'2026-04-18 19:07:47.768918'),(12,4,'Compliance Officer',1,'2026-04-18 19:07:47.768918'),(13,4,'Risk Analyst',1,'2026-04-18 19:07:47.768918'),(14,5,'Project Manager',1,'2026-04-18 19:07:47.768918'),(15,5,'Operations Manager',1,'2026-04-18 19:07:47.768918'),(16,5,'Team Lead',1,'2026-04-18 19:07:47.768918');
/*!40000 ALTER TABLE `job_title` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `new_hire`
--

DROP TABLE IF EXISTS `new_hire`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `new_hire` (
  `id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `first_name` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `middle_name` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_name` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `phone` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dob` date DEFAULT NULL,
  `gov_id` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `street` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `state` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `postal_code` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `country` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `employment_type` enum('employee','contractor') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'employee',
  `department` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `job_title` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `manager` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `start_date` date DEFAULT NULL,
  `status` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime(6) DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_new_hire_email` (`email`),
  KEY `idx_new_hire_employment_type` (`employment_type`),
  KEY `idx_new_hire_job_title` (`job_title`),
  CONSTRAINT `fk_new_hire_user_email` FOREIGN KEY (`email`) REFERENCES `user` (`email`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `new_hire`
--

LOCK TABLES `new_hire` WRITE;
/*!40000 ALTER TABLE `new_hire` DISABLE KEYS */;
INSERT INTO `new_hire` VALUES ('8b412f82c5bd1a55','Bryan','Y','Santiago','email2@gmail.com','7879905674','2001-02-03','1231231234','12','Barceloneta','PR','00617','US','employee','HR',NULL,'Bryan Hernandez','2025-12-03','pending_document_submission','2025-12-03 22:37:18.129330'),('ac0541c6076f1907','k','k','k','paolihr@paoli.com','1231231234','2004-05-05','1231231234','123 calle la calle','Barceloneta','PR','00617','US','employee','hr',NULL,'f','2026-05-18','pending_document_submission','2026-04-17 20:52:02.000000'),('aef22b9569b34a8f','Test','','User','testuser2@gmail.com','7871119999',NULL,'','123 calle real','barceloneta','PR','00617','US','employee','IT',NULL,'',NULL,'pending_document_submission','2026-04-18 18:30:26.000000');
/*!40000 ALTER TABLE `new_hire` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `new_hire_attachment`
--

DROP TABLE IF EXISTS `new_hire_attachment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `new_hire_attachment` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `hire_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `att_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `original_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stored_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `url` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_new_hire_attachment_type` (`hire_id`,`att_type`),
  KEY `hire_id` (`hire_id`),
  CONSTRAINT `new_hire_attachment_ibfk_1` FOREIGN KEY (`hire_id`) REFERENCES `new_hire` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `new_hire_attachment`
--

LOCK TABLES `new_hire_attachment` WRITE;
/*!40000 ALTER TABLE `new_hire_attachment` DISABLE KEYS */;
INSERT INTO `new_hire_attachment` VALUES (1,'8b412f82c5bd1a55','offer_letter','biometric-passport-mockup-in-human-hand-illustration-vector.jpg','8b412f82c5bd1a55_offer_letter_biometric-passport-mockup-in-human-hand-illustration-vector.jpg','/uploads/hires/8b412f82c5bd1a55_offer_letter_biometric-passport-mockup-in-human-hand-illustration-vector.jpg'),(2,'8b412f82c5bd1a55','nda','biometric-passport-mockup-in-human-hand-illustration-vector.jpg','8b412f82c5bd1a55_nda_biometric-passport-mockup-in-human-hand-illustration-vector.jpg','/uploads/hires/8b412f82c5bd1a55_nda_biometric-passport-mockup-in-human-hand-illustration-vector.jpg'),(3,'8b412f82c5bd1a55','w4','biometric-passport-mockup-in-human-hand-illustration-vector.jpg','8b412f82c5bd1a55_w4_biometric-passport-mockup-in-human-hand-illustration-vector.jpg','/uploads/hires/8b412f82c5bd1a55_w4_biometric-passport-mockup-in-human-hand-illustration-vector.jpg');
/*!40000 ALTER TABLE `new_hire_attachment` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `policy_ack`
--

DROP TABLE IF EXISTS `policy_ack`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `policy_ack` (
  `id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `policy_id` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `signature` text COLLATE utf8mb4_unicode_ci,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reviewed_by` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reviewed_at` datetime(6) DEFAULT NULL,
  `reviewer_note` text COLLATE utf8mb4_unicode_ci,
  `signed_at` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_policy_ack_email_policy` (`email`,`policy_id`),
  KEY `idx_policy_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `policy_ack`
--

LOCK TABLES `policy_ack` WRITE;
/*!40000 ALTER TABLE `policy_ack` DISABLE KEYS */;
INSERT INTO `policy_ack` VALUES ('8ba3dfa7e6c8a8c2','testuser2@gmail.com','billing_manual','f','signed',NULL,NULL,NULL,'2026-05-18 13:39:35.000000');
/*!40000 ALTER TABLE `policy_ack` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `policy_definition`
--

DROP TABLE IF EXISTS `policy_definition`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `policy_definition` (
  `policy_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `label` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `file_path` varchar(512) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  `updated_by` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`policy_id`),
  KEY `idx_policy_definition_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `policy_definition`
--

LOCK TABLES `policy_definition` WRITE;
/*!40000 ALTER TABLE `policy_definition` DISABLE KEYS */;
INSERT INTO `policy_definition` VALUES ('company_policies','Company Policies','policies/company_policies.pdf',1,'2026-05-19 19:47:37.588035','2026-05-19 20:38:21.091232','compliance.admin@paoli.local'),('medical_plan','Medical Plan Policy','policies/medical_plan_policy.pdf',1,'2026-05-19 19:47:37.588035','2026-05-19 19:47:37.588035','migration_20260519');
/*!40000 ALTER TABLE `policy_definition` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `role`
--

DROP TABLE IF EXISTS `role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `role` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_role_name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=41 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `role`
--

LOCK TABLES `role` WRITE;
/*!40000 ALTER TABLE `role` DISABLE KEYS */;
INSERT INTO `role` VALUES (1,'employee',1,'2026-05-18 12:57:14.000000'),(2,'contractor',1,'2026-05-18 12:57:14.000000'),(3,'manager',1,'2026-05-18 12:57:14.000000'),(4,'admin',1,'2026-05-18 12:57:14.000000'),(5,'superadmin',1,'2026-05-18 12:57:14.000000');
/*!40000 ALTER TABLE `role` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `task`
--

DROP TABLE IF EXISTS `task`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `task` (
  `id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `owner_email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `assigned_by` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `category` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `due_date` date DEFAULT NULL,
  `created_at` datetime(6) DEFAULT NULL,
  `updated_at` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_task_owner` (`owner_email`),
  KEY `idx_task_category` (`category`),
  KEY `idx_task_status` (`status`),
  KEY `idx_task_updated_at` (`updated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task`
--

LOCK TABLES `task` WRITE;
/*!40000 ALTER TABLE `task` DISABLE KEYS */;
/*!40000 ALTER TABLE `task` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `training_completion`
--

DROP TABLE IF EXISTS `training_completion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `training_completion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `module_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `completed_at` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_training_completion_email_module` (`email`,`module_id`),
  KEY `idx_train_email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `training_completion`
--

LOCK TABLES `training_completion` WRITE;
/*!40000 ALTER TABLE `training_completion` DISABLE KEYS */;
INSERT INTO `training_completion` VALUES (1,'testuser2@gmail.com','handbook','2026-05-18 13:55:54.000000'),(2,'testuser2@gmail.com','security101','2026-05-18 13:55:54.000000'),(3,'testuser2@gmail.com','tools','2026-05-18 13:55:55.000000');
/*!40000 ALTER TABLE `training_completion` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `training_module`
--

DROP TABLE IF EXISTS `training_module`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `training_module` (
  `id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `training_module`
--

LOCK TABLES `training_module` WRITE;
/*!40000 ALTER TABLE `training_module` DISABLE KEYS */;
INSERT INTO `training_module` VALUES ('handbook','Employee Handbook','Review company policies'),('security101','Security 101','Basic security practices'),('tools','Tools Orientation','Intro to internal tools');
/*!40000 ALTER TABLE `training_module` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user` (
  `email` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `full_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'employee',
  `role_id` bigint DEFAULT NULL,
  `department` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `department_id` bigint DEFAULT NULL,
  `job_title` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `avatar_url` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime(6) DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`email`),
  UNIQUE KEY `uq_user_id` (`id`),
  KEY `idx_user_job_title` (`job_title`),
  KEY `idx_user_role_id` (`role_id`),
  KEY `idx_user_department_id` (`department_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user`
--

LOCK TABLES `user` WRITE;
/*!40000 ALTER TABLE `user` DISABLE KEYS */;
INSERT INTO `user` VALUES ('admin@gmail.com','0ae4318ae9cb5f02','Kevin','e7cf3ef4f17c3999a94f2c6f612e8a888e5b1026878e4e19398b23bd38ec221a','admin',4,'HR',2,NULL,'pending_hr_review','','2025-12-03 21:10:33.491004'),('compliance.admin@paoli.local','10d3671934b98869','Compliance Admin','scrypt:32768:8:1$4nmf2iEiJHcbGi9H$dbd10f3327c08fb3ca1e60b5345f49f056daf78198dd190f102b7a0099a75983d5528e827d4240f664ee17abfeb2226b8f1ab16559c8b8ade0ca818cb2a7038e','admin',4,'Compliance',4,'Compliance Officer','active',NULL,'2026-05-18 17:58:37.365009'),('email2@gmail.com','8b412f82c5bd1a55','Bryan','e7cf3ef4f17c3999a94f2c6f612e8a888e5b1026878e4e19398b23bd38ec221a','admin',4,'IT',3,NULL,'pending_hr_review','/uploads/profile/96772984cd426091_pngtree-handsome-business-man-in-coat-tie-png-image_13066801.png','2025-12-03 21:21:07.386833'),('hr.admin@paoli.local','bbf47572d8ae0495','HR Admin','scrypt:32768:8:1$FqY5J1rXsOjOqT2o$7f6f760254358753e4be17ff1b3b0a68ce0c31908ba96e694202cdfdff0bb1fcfe69fa0721f7aa03f18e7e07032714ccde893bd5f795f836fb54f236f1e1d82b','admin',4,'HR',2,NULL,'active',NULL,'2026-04-18 14:03:48.000000'),('hr@paoli.local','hracct0000000001','HR Admin','scrypt:32768:8:1$QFqwkOxAVy8BJxBE$c5e3e33725af573771c75e8add71911945be87ce73341ceb0ae1a0e7089a7fc58187f74019e2bb022a091bdee914aea330b88ffa3fa078457634553965b8eb3b','admin',4,'HR',2,NULL,'active',NULL,'2026-04-17 20:42:04.000000'),('manager@paoli.local','mgracct000000001','Project Manager','scrypt:32768:8:1$TgVjeJlX7QJf4hPE$53e3c3b623a5bd587971afae6e597bddf3eaf164d36de4efcaa35e4c537129fdb659411dcf780cefc65dad01dcad725cf60be186247b0c8e82e4272d80f1d1b0','manager',3,'Management',5,'Project Manager','active',NULL,'2026-05-18 13:35:34.256336'),('newhire.employee.20260417165100@paoli.local','e7f03e92cd8c0e3c','New Hire Employee','scrypt:32768:8:1$Plg3bBg7yAf5e0KC$eeba4a4152900d4dfe800e85ec5f21ef594d65a44d88dfbb57510d20c70def8d3de2435b3e761d315df85cbf4478c96d9cf50aa777095d792d1c02b66cbe8419','employee',1,'Operations',1,NULL,'pending_hr_review',NULL,'2026-04-17 16:51:00.231329'),('paolihr@paoli.com','2ee672bbd4f6f9d6','k k k','scrypt:32768:8:1$53bNNkzg4RLlGfmx$6ca0d027e732c9266bd899d2fe9a79e5d513b79a1f07a2192cd87b7315fa6cbb4a8b63b16e9a97ce18d1377dffb78b01e7763a64635f82f67ea460d51400bf8e','employee',1,'hr',2,NULL,'pending_hr_review',NULL,'2026-04-18 00:52:02.196617'),('reviewer_hr@example.com','d3f4a5b6c7d8e9f0','HR Reviewer','scrypt:32768:8:1$uyjh47NI1VqfGTaW$cb3a2afc0783fa865d2723a41b81e1eb8158f681a8e196ed8f4e1163118ef467be3814df501e72818e2009b9d818a96af754af0cd96d3dfe6c9685386810a074','admin',4,'HR',2,NULL,'active',NULL,'2026-03-09 13:07:18.029220'),('testuser@gmail.com','c8aa52c117b2b3d6','User','e7cf3ef4f17c3999a94f2c6f612e8a888e5b1026878e4e19398b23bd38ec221a','employee',1,'Development',NULL,NULL,'pending_hr_review','/uploads/profile/96772984cd426091_pngtree-handsome-business-man-in-coat-tie-png-image_13066801.png','2025-12-03 21:21:07.386833'),('testuser2@gmail.com','a1b2c3d4e5f6a7b8','Test User','scrypt:32768:8:1$yiE3yPz3freUy62b$3140a8f0d62cba84a1a010ae1043c19547465ab4df0c004f8af0bae6f47cba962096c7a80b4d25c5509ebc5a2a89e7a813e4e27dfa77d206825dfe609b56a0a9','employee',1,'IT',3,NULL,'pending_hr_review','/uploads/profile/3efb90bc60d4f721_Image_8-21-25_at_2.22_AM.jpeg','2026-03-09 12:26:31.000000');
/*!40000 ALTER TABLE `user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping events for database 'palogroup'
--

--
-- Dumping routines for database 'palogroup'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-05-19 21:30:58
