-- MariaDB dump 10.19-11.7.2-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: webapp
-- ------------------------------------------------------
-- Server version	11.7.2-MariaDB-ubu2404

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;


CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `name` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ;


--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;


UNLOCK TABLES;

--
-- Table structure for table `passwordresets`
--

DROP TABLE IF EXISTS `passwordresets`;


CREATE TABLE `passwordresets` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `user_id` INT NOT NULL,
    `token` VARCHAR(255) NOT NULL,
    `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `unique_user_reset` (`user_id`),
    KEY `fk_passwordresets_user` (`user_id`),
    CONSTRAINT `fk_passwordresets_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ;


--
-- Dumping data for table `passwordresets`
--

LOCK TABLES `passwordresets` WRITE;


UNLOCK TABLES;

--
-- Table structure for table `urls`
--

DROP TABLE IF EXISTS `urls`;


CREATE TABLE `urls` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) DEFAULT NULL,
  `short_code` varchar(20) NOT NULL,
  `original_url` text NOT NULL,
  `expiration_date` timestamp NULL DEFAULT NULL,
  `click_count` int(11) DEFAULT 0,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `short_code` (`short_code`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `urls_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ;


--
-- Dumping data for table `urls`
--

LOCK TABLES `urls` WRITE;


UNLOCK TABLES;

--
-- Table structure for table `validatedemails`
--

DROP TABLE IF EXISTS `validatedemails`;


CREATE TABLE `validatedemails` (
  `user_id` int(11) NOT NULL,
  `validated_at` timestamp NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`user_id`),
  CONSTRAINT `validatedemails_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ;


--
-- Dumping data for table `validatedemails`
--

LOCK TABLES `validatedemails` WRITE;


UNLOCK TABLES;

--
-- Dumping routines for database 'webapp'
--

DROP PROCEDURE IF EXISTS `check_if_user_verified`;
DELIMITER ;;
CREATE PROCEDURE `check_if_user_verified`(IN id INT)
BEGIN
    SELECT user_id from validatedemails where user_id = id;
END ;;
DELIMITER ;


DROP PROCEDURE IF EXISTS `create_url`;
DELIMITER ;;
CREATE PROCEDURE `create_url`(
    IN short_code VARCHAR(20),
    IN original_url TEXT,
    IN user_id INT,
    IN expiration_date TIMESTAMP
)
BEGIN
    INSERT INTO urls (short_code, original_url, user_id, expiration_date) 
    VALUES (short_code, original_url, user_id, expiration_date);
END ;;
DELIMITER ;


DROP PROCEDURE IF EXISTS `create_user`;
DELIMITER ;;
CREATE PROCEDURE `create_user`(
    IN user_name VARCHAR(255),
    IN user_email VARCHAR(255),
    IN password_hash CHAR(64) 
)
BEGIN
    INSERT INTO users (name, email, password_hash) VALUES (user_name, user_email, password_hash);
END ;;
DELIMITER ;


DROP PROCEDURE IF EXISTS `delete_url`;
DELIMITER ;;
CREATE PROCEDURE `delete_url`(IN short_code VARCHAR(20), IN user_id INT)
BEGIN
    DELETE FROM urls WHERE short_code = short_code AND user_id = user_id;
END ;;
DELIMITER ;


DROP PROCEDURE IF EXISTS `edit_url`;
DELIMITER ;;
CREATE PROCEDURE `edit_url`(
    IN user_id INT,
    IN short_code VARCHAR(20),
    IN new_original_url TEXT
)
BEGIN
    
    IF EXISTS (SELECT 1 FROM urls WHERE short_code = short_code AND user_id = user_id) THEN
        
        UPDATE urls 
        SET original_url = new_original_url 
        WHERE short_code = short_code AND user_id = user_id;
        
        SELECT 'URL updated successfully' AS status;
    ELSE
        SELECT 'Error: You do not have permission to edit this URL' AS status;
    END IF;
END ;;
DELIMITER ;


DROP PROCEDURE IF EXISTS `get_clicks`;
DELIMITER ;;
CREATE PROCEDURE `get_clicks`(IN short_code VARCHAR(20))
BEGIN
    SELECT click_count FROM urls WHERE short_code = short_code;
END ;;
DELIMITER ;


DROP PROCEDURE IF EXISTS `get_name_by_email`;
DELIMITER ;;
CREATE PROCEDURE `get_name_by_email`(IN user_email VARCHAR(255))
BEGIN
    SELECT name FROM users where email = user_email;
END ;;
DELIMITER ;


DROP PROCEDURE IF EXISTS `get_reset_token`;
DELIMITER ;;
CREATE PROCEDURE `get_reset_token`(
    IN id INT
)
BEGIN
    SELECT token from passwordresets where user_id = id;
END ;;
DELIMITER ;


DROP PROCEDURE IF EXISTS `get_url`;
DELIMITER ;;
CREATE PROCEDURE `get_url`(IN short_code VARCHAR(20))
BEGIN
    SELECT original_url FROM urls WHERE short_code = short_code;
END ;;
DELIMITER ;


DROP PROCEDURE IF EXISTS `get_userid_by_email`;
DELIMITER ;;
CREATE PROCEDURE `get_userid_by_email`(IN user_email VARCHAR(255))
BEGIN
    SELECT id FROM users where email = user_email;
END ;;
DELIMITER ;


DROP PROCEDURE IF EXISTS `get_user_urls`;
DELIMITER ;;
CREATE PROCEDURE `get_user_urls`(IN user_id INT)
BEGIN
    SELECT id, short_code, original_url, expiration_date, click_count FROM urls WHERE user_id = user_id;
END ;;
DELIMITER ;


DROP PROCEDURE IF EXISTS `login`;
DELIMITER ;;
CREATE PROCEDURE `login`(
    IN user_email VARCHAR(255),
    IN password_attempt CHAR(64) 
)
BEGIN
    DECLARE stored_hash CHAR(64);
    SELECT password_hash INTO stored_hash FROM users WHERE email = user_email;
    
    IF stored_hash IS NOT NULL AND stored_hash = password_attempt THEN
        SELECT 'Login Successful' AS status;
    ELSE
        SELECT 'Invalid Credentials' AS status;
    END IF;
END ;;
DELIMITER ;


DROP PROCEDURE IF EXISTS `log_click`;
DELIMITER ;;
CREATE PROCEDURE `log_click`(IN short_code VARCHAR(20))
BEGIN
    UPDATE urls SET click_count = click_count + 1 WHERE short_code = short_code;
END ;;
DELIMITER ;


DROP PROCEDURE IF EXISTS `reset_password`;
DELIMITER ;;
CREATE PROCEDURE `reset_password`(
    IN user_email VARCHAR(255),
    IN reset_token CHAR(64),
    IN new_password_hash CHAR(64) 
)
BEGIN
    DECLARE user_id INT DEFAULT NULL;
    
    SELECT pr.user_id INTO user_id 
    FROM passwordresets pr
    JOIN users u ON pr.user_id = u.id
    WHERE u.email = user_email
    AND BINARY pr.token = reset_token  -- Ensure case-sensitive match
    AND pr.created_at >= NOW() - INTERVAL 3 HOUR;

    IF user_id IS NOT NULL THEN
        -- Update password
        UPDATE users SET password_hash = new_password_hash WHERE id = user_id;
        
        -- Remove token after use
        DELETE FROM passwordresets WHERE user_id = user_id AND BINARY token = reset_token;

        SELECT 'Password reset successful' AS status;
    ELSE
        SELECT 'Invalid or expired reset token' AS status;
    END IF;
END ;;
DELIMITER ;


DROP PROCEDURE IF EXISTS `set_reset_token`;
DELIMITER ;;
CREATE PROCEDURE `set_reset_token`(
    IN user_id INT,
    IN token CHAR(64) 
)
BEGIN
    DELETE FROM passwordresets WHERE user_id = user_id;
    INSERT INTO passwordresets (user_id, token, created_at) VALUES (user_id, token, NOW());
END ;;
DELIMITER ;


DROP PROCEDURE IF EXISTS `update_url_expiration`;
DELIMITER ;;
CREATE PROCEDURE `update_url_expiration`(
    IN short_code VARCHAR(20),
    IN new_expiration TIMESTAMP
)
BEGIN
    UPDATE urls SET expiration_date = new_expiration WHERE short_code = short_code;
END ;;
DELIMITER ;


DROP PROCEDURE IF EXISTS `update_user_email`;
DELIMITER ;;
CREATE PROCEDURE `update_user_email`(
    IN user_id INT,
    IN new_email VARCHAR(255)
)
BEGIN
    UPDATE users SET email = new_email WHERE id = user_id;
    DELETE FROM validatedemails WHERE user_id = user_id; 
END ;;
DELIMITER ;


DROP PROCEDURE IF EXISTS `update_user_name`;
DELIMITER $$
CREATE PROCEDURE `update_user_name`(
    IN p_user_id INT,
    IN p_new_name VARCHAR(100)
)
BEGIN
    UPDATE users
    SET name = p_new_name
    WHERE id = p_user_id;
END$$
DELIMITER ;


DROP PROCEDURE IF EXISTS `update_user_email`;
DELIMITER $$
CREATE PROCEDURE `update_user_email`(
    IN p_user_id INT,
    IN p_new_email VARCHAR(100)
)
BEGIN
    UPDATE users
    SET email = p_new_email
    WHERE id = p_user_id;

    DELETE FROM validatedemails
    WHERE user_id = p_user_id;
END$$
DELIMITER ;


DROP PROCEDURE IF EXISTS `delete_user_account`;
DELIMITER $$
CREATE PROCEDURE `delete_user_account`(
    IN p_user_id INT
)
BEGIN
    DELETE FROM urls
    WHERE user_id = p_user_id;

    DELETE FROM validatedemails
    WHERE user_id = p_user_id;

    DELETE FROM passwordresets
    WHERE user_id = p_user_id;

    DELETE FROM users
    WHERE id = p_user_id;
END$$
DELIMITER ;


DROP PROCEDURE IF EXISTS `verify_user`;
DELIMITER ;;
CREATE PROCEDURE `verify_user`(IN user_id INT)
BEGIN
    INSERT INTO validatedemails (user_id) VALUES (user_id);
END ;;
DELIMITER ;

-- Dump completed on 2025-03-18 13:46:47