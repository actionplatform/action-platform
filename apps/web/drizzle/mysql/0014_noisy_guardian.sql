CREATE TABLE `api_token_client` (
	`id` varchar(36) NOT NULL,
	`token_id` varchar(36) NOT NULL,
	`name` varchar(120) NOT NULL,
	`first_seen_at` timestamp NOT NULL DEFAULT (now()),
	`last_seen_at` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `api_token_client_id` PRIMARY KEY(`id`)
);
ALTER TABLE `api_token_client` ADD CONSTRAINT `api_token_client_token_id_api_token_id_fk` FOREIGN KEY (`token_id`) REFERENCES `api_token`(`id`) ON DELETE cascade ON UPDATE no action;