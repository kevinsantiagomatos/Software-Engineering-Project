-- MySQL dump 10.13  Distrib 8.0.40, for macos14 (arm64)
--
-- Host: localhost    Database: palogroup
-- ------------------------------------------------------
-- Server version	5.5.5-10.4.28-MariaDB

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
-- Table structure for table `new_hire_attachment`
--

DROP TABLE IF EXISTS `new_hire_attachment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `new_hire_attachment` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `hire_id` varchar(32) NOT NULL,
  `att_type` varchar(64) NOT NULL,
  `original_name` varchar(255) DEFAULT NULL,
  `stored_name` varchar(255) DEFAULT NULL,
  `url` varchar(512) DEFAULT NULL,
  PRIMARY KEY (`id`),
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
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-12-03 21:28:56
