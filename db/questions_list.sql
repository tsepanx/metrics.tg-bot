

-- Print all questions list
SELECT q.name, qt.notation_str, q.fulltext FROM question_type AS qt
    JOIN question q
        ON qt.id = q.type_id;