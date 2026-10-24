WITH averages AS (
    SELECT s.class, s.name, ROUND(AVG(g.grade), 2) AS avg_grade
    FROM students s
    JOIN grades g ON g.student_id = s.id
    GROUP BY s.id
),
ranked AS (
    SELECT class, name, avg_grade,
           DENSE_RANK() OVER (PARTITION BY class ORDER BY avg_grade DESC) AS rank
    FROM averages
)
SELECT class, name, avg_grade, rank
FROM ranked
WHERE rank <= 3
ORDER BY class, rank, name;
