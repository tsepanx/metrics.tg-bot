SELECT date, time, e.name, text FROM answer
    LEFT OUTER JOIN event e on answer.event_fk = e.pk
WHERE event_fk IS NOT NULL
ORDER BY date, time;

SELECT * FROM answer WHERE
(SELECT name FROM event WHERE event.name = event_fk);

-- (SELECT name FROM event WHERE event.name = event_fk);

SELECT *, replace(name, 'food_eat', 'food_intake') FROM event ;

UPDATE event SET name = REPLACE(name, 'cereals', 'Cereals');
-- UPDATE event SET name = initcap(name);
--     WHERE name LIKE '%food%';


-- UPDATE event SET order_by = capi;
SELECT initcap(event.name) as Nname FROM event ORDER BY order_by;


SELECT * FROM answer a
    JOIN event e on e.pk = a.event_fk
WHERE e.name LIKE 'Finances 🏦/Spend%'
ORDER BY a.date, a.time;
