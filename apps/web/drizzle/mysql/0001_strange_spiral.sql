CREATE TABLE `device_code` (
	`id` varchar(36) NOT NULL,
	`device_code` varchar(255) NOT NULL,
	`user_code` varchar(32) NOT NULL,
	`user_id` varchar(36),
	`expires_at` timestamp NOT NULL,
	`status` varchar(16) NOT NULL,
	`last_polled_at` timestamp,
	`polling_interval` int,
	`client_id` text,
	`scope` text,
	CONSTRAINT `device_code_id` PRIMARY KEY(`id`)
);
