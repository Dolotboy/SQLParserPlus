CREATE TABLE contract(
id BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT, 
contract_number VARCHAR(25) NOT NULL,`state` ENUM('open', 'closed') NOT NULL,`role` ENUM('admin','member') NOT NULL, 
user_id BIGINT NOT NULL,fees_amount DECIMAL(10,2) NOT NULL,taxes_amount DECIMAL(10, 2) NOT NULL, 
client_id BIGINT NOT NULL
);

ALTER TABLE contract
ADD FOREIGN KEY (user_id) REFERENCES user(id),
ADD FOREIGN KEY (client_id) REFERENCES client(id);