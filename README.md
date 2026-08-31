# SQLParser+

SQLParser+ is a Python-based SQL parser and model builder for MySQL-style scripts. It reads a SQL file, extracts the statements, reconstructs the database model, and exports a structured JSON representation that can then be used for catalog generation, UML modeling, SQL translation, or lineage analysis.

From this JSON you can:
- Create an UML diagram of your database
- Export a data catalog or schema inventory
- Reconstruct lineage and dependency information
- Translate a script into another SQL dialect
- Rebuild a normalized in-memory representation of the database

The parser also includes an auto-format layer to normalize common formatting issues before extraction.

## Installation

### Dependencies
- [Python 3.12](https://www.python.org/downloads/)
- [Venv]()
  ```bash
  sudo apt install python3-venv
  ```
- [PIP]()
  ```bash
  sudo apt install python3-pip
  ```
- [Tkinter]()
  ```bash
  sudo apt install python3-tk
  ```

### Cloning Procedure
```bash
git clone https://github.com/Dolotboy/SQLParserPlus.git
```

## Launch
1. ```bash
   python3 -m venv venv
   ```
2. ```bash
   source venv/bin/activate
   ```
3. ```bash
   python3 app.pyw
   ```

## Correct Format

The parser is designed to be resilient, but the following formatting rules help keep extraction accurate and deterministic.

- (Managed by Auto Format) Each CREATE TABLE column definition should end in a clear delimiter structure
- (Managed by Auto Format) DECIMAL values should not contain spaces inside the type declaration, for example: DECIMAL(10,2)
- (Managed by Auto Format) ENUM values should not contain spaces inside the declaration, for example: ENUM('user','admin')
- (Managed by Auto Format) Table and column identifiers should be normalized to remove backticks before internal processing

---

## Technical

The parser follows a straightforward pipeline:

1. Load the SQL file
2. Strip comments and normalize spacing/formatting
3. Split the script into statement blocks
4. Detect object types such as CREATE TABLE, CREATE VIEW, and ALTER TABLE
5. Instantiate model objects
6. Apply ALTER statements to the in-memory schema
7. Serialize the model to JSON or rebuild SQL output

### Core parsing flow

- Script.format(): reads the file, removes comment lines, normalizes commas, strips spaces inside DECIMAL and ENUM declarations, and prepares a clean script text.
- Script.extract_queries_create_table(): scans the script for CREATE TABLE blocks and instantiates QueryCreateTable.
- Script.extract_queries_create_view(): scans for CREATE VIEW blocks and instantiates QueryCreateView.
- Script.extract_queries_alter_table(): identifies ALTER TABLE queries, splits them into statement units, and builds QueryAlterTable objects.
- DB.build_model(): applies create statements first, then alter statements, in a way that reflects the real execution order of the schema.

### Main classes

#### Column
Represents one column in a table.

Attributes:
- name
- dataType
- attributes
- referenceTable
- referenceColumn

The parser keeps the base SQL type separately from modifier keywords. For example:
- dataType: bigint(20)
- attributes: ["UNSIGNED", "NOT", "NULL", "AUTO_INCREMENT"]

This allows the model to reflect the actual MySQL column definition without polluting the type with modifiers.

#### Table
Represents a database table.

Attributes:
- name
- columns[]

It can be serialized to JSON or rebuilt into SQL via to_sql().

#### View
Represents a view definition.

Attributes:
- name
- columns[]

Each view column tracks:
- name
- actualName
- sourceTable

#### AlterStatement
Represents one ALTER TABLE action.

Supported data captured:
- alterType
- alterText
- concernedColumn
- columnReferenceTable
- columnReferenceColumn
- columnName
- newColumnName
- newColumnType
- newColumnAttributes

This object is the bridge between the raw ALTER statement and the modification applied to the in-memory model.

#### QueryCreateTable / QueryCreateView / QueryAlterTable
These query wrappers extract structured data from each SQL block and then feed the main DB model.

#### Script
The Script object stores the full text and the extracted queries grouped by category:
- queriesCreateTable
- queriesCreateView
- queriesAlterTable

#### DB
The DB object is the final model container. It stores:
- tables[]
- views[]
- script

It is the object used to reconstruct the database schema after reading the whole script.

---

## Structure (Objects)

The model is intentionally simple and hierarchical.

```python
DB
├── tables: [Table]
├── views: [View]
└── script: Script

Table
├── name: str
└── columns: [Column]

Column
├── name: str
├── dataType: str
├── attributes: [str]
├── referenceTable: str | None
├── referenceColumn: str | None
└── ...

View
├── name: str
└── columns: [ViewColumn]

ViewColumn
├── name: str
├── actualName: str | None
├── sourceTable: str | None
└── ...
```

### Example of column normalization

```sql
id bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT
```

becomes internally:

```python
{
  "name": "id",
  "dataType": "bigint(20)",
  "attributes": ["UNSIGNED", "NOT", "NULL", "AUTO_INCREMENT"]
}
```

This is important because the parser must distinguish actual SQL type declarations from integrity or index modifiers.

---

## ALTER handling and application order

ALTER statements are not processed as simple text fragments; they are parsed into typed operations and then applied in a deterministic order.

### 1. Statement detection
The parser uses regex-based detection to locate ALTER TABLE blocks and split them into individual actions.

Common detected patterns include:
- ADD PRIMARY KEY
- ADD UNIQUE KEY
- ADD KEY / ADD INDEX
- ADD COLUMN
- ADD CONSTRAINT ... FOREIGN KEY
- DROP COLUMN
- RENAME COLUMN
- ALTER COLUMN / MODIFY COLUMN
- DROP
- RENAME

### 2. Statement classification
Each ALTER fragment is mapped to an alterType with rules such as:
- ADD FOREIGN KEY
- ADD PRIMARY KEY
- ADD UNIQUE KEY
- ADD KEY
- ADD INDEX
- ADD
- DROP COLUMN
- RENAME COLUMN
- ALTER COLUMN
- MODIFY COLUMN
- MODIFY
- RENAME

The rules also ensure that true constraint statements are not confused with ordinary column additions.

### 3. Statement extraction and normalization
For each action:
- the table name is extracted from ALTER TABLE x
- the table prefix is removed from the statement text
- the action is normalized and stored in AlterStatement
- column names and type definitions are parsed
- foreign key metadata is captured when a reference is declared

Example:

```sql
ALTER TABLE model_has_permissions
  ADD CONSTRAINT model_has_permissions_permission_id_foreign FOREIGN KEY (permission_id) REFERENCES permissions (id) ON DELETE CASCADE;
```

is stored as a foreign-key alter where:
- concernedColumn = permission_id
- columnReferenceTable = permissions
- columnReferenceColumn = id

### 4. Application to the model
Once the CREATE TABLE objects are loaded, DB.build_model() iterates the ALTER statements in script order and applies them to the matching table.

The order of updates is important:

- FOREIGN KEY metadata is attached first when the constraint references an existing column
- ADD operations are only applied when they are actual column additions, not if they are index or constraint declarations
- DROP and RENAME remove or rename existing columns
- MODIFY / ALTER COLUMN updates the type and attributes on the matching column

This avoids creating fake columns such as PRIMARY, CONSTRAINT, KEY, or FOREIGN as if they were real table fields.

### 5. Why ordering matters
The parser intentionally applies CREATE and ALTER statements in a stable sequence to preserve the real database model. This is especially important for:
- foreign keys
- PK and unique constraints
- auto-increment columns
- rename or drop operations after creation

The result is a schema that reflects the original MySQL script more faithfully than a naive line-by-line extraction.

---

## Scaling

The current implementation is intentionally lightweight and is designed for moderate SQL dumps and migration scripts.

### Current performance profile
- Complexity is effectively linear in the size of the script for extraction and building
- Regular-expression scanning is fast for standard schema files and migration batches
- The model is kept in memory as Python objects, which is enough for medium-sized database definitions

### Strengths
- simple to understand and debug
- easy to extend
- suitable for schema introspection and JSON-based tooling
- robust enough for MySQL-style migration scripts

### Scaling limits
For very large scripts, or for advanced SQL dialects, the current regex-based approach can become harder to maintain because:
- nested SQL constructs are more complex to parse reliably
- dialect-specific features may require richer grammar handling
- large output sets may benefit from AST-based processing rather than regex splitting

### Recommended evolution path
For bigger scale or production-grade parsing, a next step would be to move from regex scanning to a dedicated SQL parser or a grammar-driven tokenizer, while keeping the current object model as the canonical in-memory representation.

---

## Supported

The parser currently supports the following SQL statement families, with the emphasis on MySQL-style schema definitions.

### CREATE TABLE
Supported:
- CREATE TABLE name (...)
- column definitions with base types
- type modifiers such as UNSIGNED
- NULL / NOT NULL
- DEFAULT
- AUTO_INCREMENT
- PRIMARY KEY declarations inside column definitions
- UNIQUE declarations inside column definitions
- KEY / INDEX declarations

Example:
```sql
CREATE TABLE users (
  id bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  email varchar(255) NOT NULL,
  PRIMARY KEY (id)
);
```

### CREATE VIEW
Supported:
- CREATE VIEW name AS SELECT ...
- simple column aliases
- source table qualification like table.column
- optional AS alias usage
- FROM clauses with one or more tables

Example:
```sql
CREATE VIEW active_users AS
SELECT u.id, u.email AS user_email
FROM users u;
```

### Constraints and keys
Supported:
- PRIMARY KEY
- UNIQUE KEY
- KEY
- INDEX
- FOREIGN KEY
- CONSTRAINT name FOREIGN KEY ... REFERENCES ...

The parser tracks foreign-key relationships by joining:
- source column
- referenced table
- referenced column

### ALTER TABLE
Supported operation families:
- ADD COLUMN
- ADD PRIMARY KEY
- ADD UNIQUE KEY
- ADD KEY
- ADD INDEX
- ADD CONSTRAINT ... FOREIGN KEY
- DROP COLUMN
- DROP
- RENAME COLUMN
- RENAME
- ALTER COLUMN
- MODIFY COLUMN
- MODIFY

Examples:
```sql
ALTER TABLE users ADD COLUMN last_login timestamp NULL;
ALTER TABLE users ADD PRIMARY KEY (id);
ALTER TABLE users DROP COLUMN old_field;
ALTER TABLE users RENAME COLUMN email TO user_email;
ALTER TABLE users MODIFY id bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;
ALTER TABLE orders ADD CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users (id);
```

### Mixed script support
The parser is designed to work with real migration dumps containing:
- CREATE TABLE blocks
- CREATE VIEW blocks
- ALTER TABLE blocks
- sequential updates over multiple tables
- comments and formatting variations

### Notable behavior
- real table columns are preserved
- constraint keywords are not created as standalone fake columns
- foreign keys are linked to their referenced table and column
- type modifiers are separated from the base SQL type

---

## Authors

- [@Dolotboy](https://www.github.com/dolotboy)

