

-- Completely removes 'question_type' table

-- ALTER TABLE question_type ADD COLUMN format_str VARCHAR(255);

ALTER TABLE question DROP CONSTRAINT question_type_id_fkey;
DROP TABLE IF EXISTS question_type;

ALTER TABLE question ALTER COLUMN choices_list DROP NOT NULL;
ALTER TABLE question ALTER COLUMN choices_list TYPE VARCHAR(50)[];

UPDATE question SET choices_list = NULL WHERE name = 'sad_lamp_usage';

-- ALTER TABLE question ADD COLUMN choice2 VARCHAR(50)[] NULL;
