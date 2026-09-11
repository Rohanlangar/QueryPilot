/**
 * Basic SQL formatter for display purposes.
 * Adds line breaks and indentation for readability.
 */
export function formatSQL(sql) {
  if (!sql) return '';

  const keywords = [
    'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN',
    'INNER JOIN', 'OUTER JOIN', 'FULL JOIN', 'CROSS JOIN', 'ON', 'GROUP BY',
    'ORDER BY', 'HAVING', 'LIMIT', 'OFFSET', 'UNION', 'UNION ALL',
    'INSERT INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE FROM', 'CREATE TABLE',
    'ALTER TABLE', 'DROP TABLE', 'WITH', 'AS', 'CASE', 'WHEN', 'THEN', 'ELSE',
    'END', 'IN', 'NOT IN', 'EXISTS', 'NOT EXISTS', 'BETWEEN', 'LIKE',
    'IS NULL', 'IS NOT NULL', 'ASC', 'DESC', 'DISTINCT', 'TOP', 'FETCH',
  ];

  let formatted = sql.trim();

  // Normalize whitespace
  formatted = formatted.replace(/\s+/g, ' ');

  // Add newlines before major keywords
  const majorKeywords = [
    'SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT',
    'UNION', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 'OUTER JOIN',
    'WITH', 'INSERT INTO', 'UPDATE', 'DELETE FROM', 'SET', 'VALUES',
  ];

  majorKeywords.forEach((kw) => {
    const regex = new RegExp(`\\b(${kw})\\b`, 'gi');
    formatted = formatted.replace(regex, `\n${kw}`);
  });

  // Indent sub-clauses
  formatted = formatted
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .join('\n');

  return formatted;
}
