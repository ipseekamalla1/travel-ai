-- Runs once when the local Postgres volume is first created.
-- A separate database for the test suite so tests never touch development data.
CREATE DATABASE atu_test;
