PRAGMA foreign_keys=OFF;
CREATE TABLE `__new_api_token` (
	`id` text PRIMARY KEY NOT NULL,
	`user_id` text NOT NULL,
	`organization_id` text,
	`name` text NOT NULL,
	`scope` text NOT NULL,
	`project_id` text,
	`app_id` text,
	`created_at` integer NOT NULL,
	`expires_at` integer NOT NULL,
	`last_used_at` integer,
	`revoked_at` integer,
	FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`organization_id`) REFERENCES `organization`(`id`) ON UPDATE no action ON DELETE cascade
);
INSERT INTO `__new_api_token`("id", "user_id", "organization_id", "name", "scope", "project_id", "app_id", "created_at", "expires_at", "last_used_at", "revoked_at") SELECT "id", "user_id", "organization_id", "name", "scope", "project_id", "app_id", "created_at", "expires_at", "last_used_at", "revoked_at" FROM `api_token`;
DROP TABLE `api_token`;
ALTER TABLE `__new_api_token` RENAME TO `api_token`;
PRAGMA foreign_keys=ON;