

-- Completely removes 'question_type' table

-- ALTER TABLE question_type ADD COLUMN format_str VARCHAR(255);

ALTER TABLE question DROP CONSTRAINT question_type_id_fkey;
DROP TABLE IF EXISTS question_type;
