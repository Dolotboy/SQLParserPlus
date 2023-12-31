import re
import json

class Column:
    def __init__(self, name, dataType, attributes=None):
        self.name = name
        self.dataType = dataType
        self.attributes = attributes
        self.referenceTable = None
        self.referenceColumn = None
    
    def add_reference(self, referenceTable, referenceColumn):
        self.referenceTable = referenceTable
        self.referenceColumn = referenceColumn
    
    def __str__(self):
        attributes_str = " ".join(self.attributes) if self.attributes else ""
        #return f"Column: {self.name} ({self.dataType}) {attributes_str}"
        return f"Column: {self.name} ({self.dataType})"
    
    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4)

class Table:
    def __init__(self, name):
        self.name = name
        self.columns = []
    
    def add_column(self, column):
        self.columns.append(column)
    
    def __str__(self):
        return f"Table: {self.name}\nColumns: {', '.join(str(col) for col in self.columns)}"
    
    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=False, indent=4)

class QueryCreateTable:
    def __init__(self, queryText):
        self.queryText = queryText
        self.table = self.extract_data()

    def extract_data(self):
        createStart = self.queryText.index("(")
        tableName = self.queryText[13:createStart].strip()
        tableInstance = Table(tableName)

        columnText = self.queryText[createStart + 1: -1]
        columnDefinitions = [part.strip() for part in columnText.split(", ")]

        for columnDef in columnDefinitions:
            columnParts = columnDef.strip().split()
            if len(columnParts) >= 2: 
                columnName = columnParts[0]
                columnType = columnParts[1]
                columnAttributes = [part for part in columnParts[2:] if part.upper() in ["PRIMARY", "KEY", "NOT", "NULL", "AUTO_INCREMENT"]]
                columnInstance = Column(columnName, columnType, columnAttributes)
                tableInstance.add_column(columnInstance)
        return tableInstance
    
    def extract_column_definitions(self, columnText):
        columnDefinitions = []
        currentColumn = ""
        openParentheses = 0

        for char in columnText:
            if char == '(':
                openParentheses += 1
            elif char == ')':
                openParentheses -= 1
            
            currentColumn += char

            if openParentheses == 0 and char == ',':
                columnDefinitions.append(currentColumn.strip())
                currentColumn = ""

        # Add the last column    
        columnDefinitions.append(currentColumn.strip())

        return columnDefinitions
    
    def __str__(self):
        return f"Query: {self.queryText}"

class QueryCreateView:
    def __init__(self, queryText):
        self.queryText = queryText
        self.viewTable = None
        self.extract_data()

    def extract_data(self):
        # Use regular expressions to extract the view name.
        view_name_match = re.search(r'CREATE\s+VIEW\s+(\w+)', self.queryText)
        if view_name_match:
            view_name = view_name_match.group(1)
            self.viewTable = Table(view_name)

        # Use regular expressions to extract columns from the SELECT statement.
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', self.queryText, re.DOTALL)
        if select_match:
            select_clause = select_match.group(1)
            column_strings = select_clause.split(',')
            for column_string in column_strings:
                column_string = column_string.strip()
                # Check for column alias using "AS" or without it
                alias_match = re.match(r'(\w+)(?:\.(\w+))?(?:\s+AS\s+(\w+))?', column_string)
                if alias_match:
                    table, column, alias = alias_match.groups()
                    if alias:
                        name = alias
                    elif column:
                        name = column
                    else:
                        name = table

                    # Extract the reference table from the column (e.g., user.id)
                    if table and column:
                        self.viewTable.add_column(Column(name, None))
                        self.viewTable.columns[-1].add_reference(table, column)
                    else:
                        self.viewTable.add_column(Column(name, None))
    
    def __str__(self):
        return f"Query: {self.queryText}"

class AlterStatement:
    def __init__(self, alterType, alterText):
        self.alterType = alterType
        self.alterText = alterText
        self.concernedColumn = None
        self.columnReferenceTable = None
        self.columnReferenceColumn = None
        self.extract_data()

    def extract_data(self):
        if self.alterType == "ADD FOREIGN KEY":
            # Extract concerned column, reference table, and reference column from the alter text.
            match = re.match(r'.*FOREIGN KEY\s+\((\w+)\)\s+REFERENCES\s+(\w+)\((\w+)\).*', self.alterText)
            if match:
                self.concernedColumn = match.group(1)
                self.columnReferenceTable = match.group(2)
                self.columnReferenceColumn = match.group(3)

class QueryAlterTable:
    def __init__(self, queryText):
        self.queryText = queryText
        self.table = None
        self.alterStatements = self.extract_data()
    
    def extract_data(self):
        # Extract the table name from the queryText.
        table_match = re.match(r'ALTER\s+TABLE\s+(\w+)\s+', self.queryText)
        if table_match:
            self.table = table_match.group(1)

        alter_statements = []
        statements = self.queryText.split(', ')
        for statement in statements:
            statement = statement.strip()
            if statement:
                alter_type = self.extract_alter_type(statement)
                alter_text = self.remove_alter_table(statement)
                alter_statements.append(AlterStatement(alter_type, alter_text))
        return alter_statements

    def remove_alter_table(self, statement):
        # Remove the "ALTER TABLE (table_name)" part from the statement.
        return re.sub(r'ALTER\s+TABLE\s+' + re.escape(self.table) + r'\s+', '', statement)

    def extract_alter_type(self, statement):
        # Define regular expressions to match alter statement types.
        alter_type_patterns = {
            "ADD FOREIGN KEY": r'ADD\s+FOREIGN\s+KEY',
            "ADD": r'ADD(?! FOREIGN KEY)',
            "DROP COLUMN": r'DROP\s+COLUMN',
            "RENAME COLUMN": r'RENAME\s+COLUMN',
            "ALTER COLUMN": r'ALTER\s+COLUMN',
            "MODIFY COLUMN": r'MODIFY\s+COLUMN',
            "MODIFY": r'MODIFY(?! COLUMN)'
        }

        for alter_type, pattern in alter_type_patterns.items():
            if re.search(pattern, statement):
                return alter_type

        return "UNKNOWN"
    
    def __str__(self):
        return f"Query: {self.queryText}"

class Script:
    def __init__(self, scriptPath):
        self.scriptText = self.format(scriptPath)
        self.queriesCreateTable = self.extract_queries_create_table()
        self.queriesCreateView = self.extract_queries_create_view()
        self.queriesAlterTable = self.extract_queries_alter_table()
        self.tables = []
        self.extract_queries_data()
    
    def format(self, scriptPath):
        scriptFile=open(scriptPath,"r")
        text = ""
        for line in scriptFile.readlines():
            # ADD SPACE AT THE END OF LINE FINISHING WITH A ","
            line = line.replace(",", ", ")
            # LOCATE DECIMAL INDEX AND REMOVE SPACE IF EXIST
            flag = True
            startIndex = 0
            while flag:
                decimalStart = line.find("DECIMAL", startIndex)
                if decimalStart != -1:
                    decimalStart = decimalStart - 1 # -1 is used to englobe the "D"
                    decimalEnd = line.find(")", decimalStart) + 1 # +1 is used to englobe the ")"
                    decimalText = line[decimalStart + 1:decimalEnd] # 1:decimalEnd is because string slice notaton is start::stop
                    newDecimalText = decimalText.replace(" ", "")
                    line = line.replace(decimalText, newDecimalText)
                    startIndex = decimalStart + 2 # Add 2 to the starting index so it can look for a new one
                else:
                    flag = False
            # LOCATE ENUM INDEX AND REMOVE SPACE IF EXIST
            flag = True
            startIndex = 0
            while flag:
                enumStart = line.find("ENUM", startIndex)
                if enumStart != -1:
                    enumStart = enumStart - 1 # -1 is used to englobe the "E"
                    enumEnd = line.find(")", enumStart) + 1 # +1 is used to englobe the ")"
                    enumText = line[enumStart + 1:enumEnd] # 1:enumEnd is because string slice notaton is start::stop
                    newEnumText = enumText.replace(" ", "")
                    line = line.replace(enumText, newEnumText)
                    startIndex = enumStart + 2 # Add 2 to the starting index so it can look for a new one
                else:
                    flag = False
            text += line
        return text
    
    def extract_queries_create_table(self):
        queries = self.scriptText.split(';')

        queryInstances = []

        for queryText in queries:
            queryInstance = None
            queryText = queryText.strip()
            if queryText:
                if "CREATE TABLE" in queryText:
                    queryInstance = QueryCreateTable(queryText)

                if queryInstance:
                    queryInstances.append(queryInstance)
        return queryInstances
    
    def extract_queries_create_view(self):
        queries = self.scriptText.split(';')

        queryInstances = []

        for queryText in queries:
            queryInstance = None
            queryText = queryText.strip()
            if queryText:
                if "CREATE VIEW" in queryText:
                    queryInstance = QueryCreateView(queryText)

                if queryInstance:
                    queryInstances.append(queryInstance)
        return queryInstances
    
    def extract_queries_alter_table(self):
        queries = self.scriptText.split(';')

        queryInstances = []

        for queryText in queries:
            queryInstance = None
            queryText = queryText.strip()
            if queryText:
                if "ALTER TABLE" in queryText:
                    queryInstance = QueryAlterTable(queryText)
                
                if queryInstance:
                    queryInstances.append(queryInstance)
        return queryInstances
    
    def extract_queries_data(self):
        # EXTRACT DATA FOR CREATE TABLE FIRST
        queriesToProceed = self.queriesCreateTable.copy() # If not using copy, it will also remove from self.queriesCreateTable
        for query in queriesToProceed[:]: # The [:] returns a "slice" of x, which happens to contain all its elements, and is thus effectively a copy of x.
            self.tables.append(query.table)
            queriesToProceed.remove(query)
        
        queriesToProceed = self.queriesCreateView.copy() # If not using copy, it will also remove from self.queriesCreateTable
        for query in queriesToProceed[:]: # The [:] returns a "slice" of x, which happens to contain all its elements, and is thus effectively a copy of x.
            self.tables.append(query.viewTable)
            queriesToProceed.remove(query)

        queriesToProceed = self.queriesAlterTable.copy() # If not using copy, it will also remove from self.queriesAlterTable
        # EXTRACT DATA FOR ALTER TABLE SECOND
        for query in queriesToProceed[:]: # The [:] returns a "slice" of x, which happens to contain all its elements, and is thus effectively a copy of x.
            query.extract_data()
            for table in self.tables:
                if table.name == query.table:
                    for alterStatement in query.alterStatements:
                        for column in table.columns:
                            if alterStatement.concernedColumn:
                                if column.name == alterStatement.concernedColumn:
                                    column.referenceTable = alterStatement.columnReferenceTable
                                    column.referenceColumn = alterStatement.columnReferenceColumn

            queriesToProceed.remove(query)
    
    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=False, indent=4)
    
    def to_str(self):
        for table in self.tables:
            print(table.__str__())

def Main():
    scriptPath = input('Enter the script path: ')
    script = Script(scriptPath)
    with open(f"E:\Programmation\Scripts\SQLParser\output.json", "w+") as outfile:
        outfile.write(script.to_json())
    input()

if __name__ == "__main__":
    Main()