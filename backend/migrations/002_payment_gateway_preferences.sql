-- Migration: Add user payment gateway/country preferences
-- Date: 2026-04-18
-- Description: Adds user-selected country and gateway override fields.

ALTER TABLE users ADD COLUMN IF NOT EXISTS selected_country VARCHAR(2);
ALTER TABLE users ADD COLUMN IF NOT EXISTS selected_gateway VARCHAR(20);
