CREATE VIEW my_view AS 
SELECT user.id AS UserID, user.name, (SELECT product.id FROM product) AS ProductID
FROM user 
JOIN orders ON user.id = orders.user_id;