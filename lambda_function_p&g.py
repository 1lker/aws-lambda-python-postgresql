import json
import os
import sys
import base64

# Add the package folder to the Python path
package_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'package')
sys.path.append(package_path)

print(f"Python version: {sys.version}")
print(f"Sys path: {sys.path}")
print(f"Package path: {package_path}")
print("Contents of package directory:")
print(os.listdir(package_path))

try:
    import pg8000
    print(f"Successfully imported pg8000 version: {pg8000.__version__}")
except ImportError as e:
    print(f"Failed to import pg8000: {str(e)}")

# RDS ayarları
RDS_HOST = os.environ['DB_HOST']
RDS_USER = os.environ['DB_USER']
RDS_PASSWORD = os.environ['DB_PASSWORD']
RDS_DATABASE = os.environ['DB_NAME']

def get_connection():
    return pg8000.connect(
        host=RDS_HOST,
        user=RDS_USER,
        password=RDS_PASSWORD,
        database=RDS_DATABASE
    )

def get_user_id(email):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        sql = "SELECT id FROM islerapp_customuser WHERE email = %s"
        cursor.execute(sql, (email,))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        connection.close()

def get_bayi_details(kullanici_id):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        sql = """
        SELECT b.id, b.kod, b.adi
        FROM islerapp_bayi b
        JOIN islerapp_bayierisim be ON b.id = be.bayi_id
        WHERE be.kullanici_id = %s
        """
        cursor.execute(sql, (kullanici_id,))
        columns = ['id', 'kod', 'adi']
        result = cursor.fetchall()
        return [dict(zip(columns, row)) for row in result]
    finally:
        connection.close()

def lambda_handler(event, context):
    print("Received event:", json.dumps(event))  # Log the entire event for debugging

    try:
        # Check if it's GET or POST request
        http_method = event.get('httpMethod', 'GET')
        
        if http_method == 'GET':
            # For GET requests, extract email from query string parameters
            query_params = event.get('queryStringParameters', {}) or {}
            email = query_params.get('email')
        elif http_method == 'POST':
            # For POST requests, extract email from body
            if event.get('isBase64Encoded', False):
                body = base64.b64decode(event['body']).decode('utf-8')
            else:
                body = event.get('body', '{}')
            body_json = json.loads(body)
            email = body_json.get('email')
        else:
            return {
                'statusCode': 405,
                'body': json.dumps({'error': 'Method not allowed'})
            }
        
        if not email:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Email is required'})
            }
        
        print(f"Processing request for email: {email}")  # Log the email being processed
        
        kullanici_id = get_user_id(email)
        print(f"User ID: {kullanici_id}")  # Log the user ID
        
        if not kullanici_id:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'User not found'})
            }
        
        bayi_details = get_bayi_details(kullanici_id)
        print(f"Bayi details: {bayi_details}")  # Log the bayi details
        
        if not bayi_details:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'No bayi found for user'})
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps(bayi_details)
        }
    
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        print(f"Error occurred: {str(e)}")  # Log any exceptions
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }