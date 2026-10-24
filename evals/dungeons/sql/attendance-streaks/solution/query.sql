WITH present AS (
    SELECT student_id, day,
           julianday(day) - ROW_NUMBER() OVER (PARTITION BY student_id ORDER BY day) AS island
    FROM attendance
    WHERE present = 1
),
streaks AS (
    SELECT student_id, MIN(day) AS start_day, COUNT(*) AS length
    FROM present
    GROUP BY student_id, island
),
best AS (
    SELECT student_id, length, start_day,
           ROW_NUMBER() OVER (PARTITION BY student_id ORDER BY length DESC, start_day) AS pick
    FROM streaks
)
SELECT student_id, length AS longest_streak, start_day AS streak_start
FROM best
WHERE pick = 1
ORDER BY longest_streak DESC, student_id;
