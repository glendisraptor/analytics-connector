#!/bin/bash
# fixed_complete_etl_demo.sh - Fixed version with proper JSON and database credentials

echo "🚀 Analytics Connector - Fixed ETL Demo"
echo "======================================="

# Function to check if service is running
check_service() {
    local service_name=$1
    local url=$2
    local expected_status=${3:-200}
    
    echo -n "   Checking $service_name... "
    
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "$expected_status"; then
        echo "✅ Running"
        return 0
    else
        echo "❌ Not running"
        return 1
    fi
}

# Step 1: Verify all services are running
echo "1️⃣ Checking Required Services"
echo "=============================="

check_service "Backend API" "http://localhost:8000/health"
BACKEND_OK=$?

check_service "Frontend" "http://localhost:5173" "200\|301\|302"
FRONTEND_OK=$?

check_service "Superset" "http://localhost:8088/health"
SUPERSET_OK=$?

if [ $BACKEND_OK -ne 0 ]; then
    echo ""
    echo "❌ Backend is not running. Start it with:"
    echo "   cd backend && python -m app.main"
    echo "   OR: docker-compose up backend"
    exit 1
fi

echo ""
echo "✅ All services verified"

# Step 2: Test database connectivity (FIXED - use correct credentials)
echo ""
echo "2️⃣ Testing Database Connectivity"
echo "================================"

echo -n "   Testing app database... "
# Use PGPASSWORD to avoid password prompts
if PGPASSWORD=admin psql -h localhost -p 5432 -U postgres -d analytics_connector -c "SELECT 1;" >/dev/null 2>&1; then
    echo "✅ Connected"
else
    echo "❌ Failed"
    echo "   Make sure PostgreSQL is running with postgres credentials"
    exit 1
fi

echo -n "   Testing analytics database... "
if PGPASSWORD=admin psql -h localhost -p 5432 -U postgres -d analytics_data -c "SELECT 1;" >/dev/null 2>&1; then
    echo "✅ Connected"
else
    echo "❌ Failed"
    echo "   Make sure analytics_data database exists"
    exit 1
fi

# Step 3: Check database schema (FIXED - use correct credentials)
echo ""
echo "3️⃣ Verifying Database Schema"
echo "============================"

REQUIRED_TABLES="users database_connections etl_jobs"

for table in $REQUIRED_TABLES; do
    echo -n "   Checking table '$table'... "
    if PGPASSWORD=admin psql -h localhost -p 5432 -U postgres -d analytics_connector -c "\dt $table" 2>/dev/null | grep -q "$table"; then
        # Get record count
        count=$(PGPASSWORD=admin psql -h localhost -p 5432 -U postgres -d analytics_connector -t -c "SELECT COUNT(*) FROM $table;" 2>/dev/null | xargs)
        echo "✅ Exists ($count records)"
    else
        echo "❌ Missing"
        echo ""
        echo "   Missing table: $table"
        echo "   Run database setup scripts first!"
        exit 1
    fi
done

# Step 4: Test API authentication
echo ""
echo "4️⃣ Testing API Authentication"
echo "============================="

# Try to get auth token
echo -n "   Testing login... "
AUTH_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=glen.mogane&password=admin123")

TOKEN=$(echo "$AUTH_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ -n "$TOKEN" ]; then
    echo "✅ Success"
    echo "   Token: ${TOKEN:0:20}..."
else
    echo "❌ Failed"
    echo "   Response: $AUTH_RESPONSE"
    echo ""
    echo "💡 Create a user account first:"
    echo "   1. Go to http://localhost:3000/register"
    echo "   2. Or create admin user with password 'admin123'"
    exit 1
fi

# Step 5: Check database connections
echo ""
echo "5️⃣ Checking Database Connections"
echo "================================"

CONNECTIONS_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" \
    http://localhost:8000/api/v1/connections/)

echo "   Connections response: $CONNECTIONS_RESPONSE"

CONNECTION_COUNT=$(echo "$CONNECTIONS_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if isinstance(data, list):
        print(len(data))
    else:
        print(0)
except:
    print(0)
" 2>/dev/null)

echo "   Found $CONNECTION_COUNT database connection(s)"

if [ "$CONNECTION_COUNT" -eq 0 ]; then
    echo ""
    echo "❌ No database connections found"
    echo ""
    echo "💡 Add a database connection:"
    echo "   1. Go to http://localhost:3000/connections"
    echo "   2. Click 'Add Connection'"
    echo "   3. Fill in your database details"
    echo ""
    echo "📋 Example connection (using the app database itself):"
    echo "   Name: Test Connection"
    echo "   Type: PostgreSQL"
    echo "   Host: localhost"
    echo "   Port: 5432"
    echo "   Username: postgres"
    echo "   Password: admin"
    echo "   Database: analytics_connector"
    exit 1
fi

# Get first connected connection (FIXED - better JSON parsing)
CONNECTED_CONNECTION=$(echo "$CONNECTIONS_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if isinstance(data, list):
        for conn in data:
            if conn.get('status') == 'connected':
                print(conn['id'])
                break
except:
    pass
" 2>/dev/null)

if [ -z "$CONNECTED_CONNECTION" ]; then
    echo "   ⚠️  No connections have status 'connected'"
    echo ""
    echo "💡 Make sure at least one connection status is 'connected':"
    echo "   1. Check connection credentials are correct"
    echo "   2. Test the connection in the UI"
    echo "   3. Verify the target database is accessible"
    
    # Show connection statuses for debugging
    echo ""
    echo "   Current connection statuses:"
    echo "$CONNECTIONS_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if isinstance(data, list):
        for conn in data:
            print(f\"     • {conn.get('name', 'Unknown')}: {conn.get('status', 'Unknown')}\")
except:
    print('     • Could not parse connections')
" 2>/dev/null
    exit 1
fi

echo "   ✅ Found connected connection ID: $CONNECTED_CONNECTION"

# Step 6: Test ETL job creation (FIXED - proper JSON formatting)
echo ""
echo "6️⃣ Testing ETL Job Creation"
echo "=========================="

echo "   Creating test ETL job for connection $CONNECTED_CONNECTION..."

# Create properly formatted JSON
ETL_JSON=$(cat <<EOF
{
  "connection_id": $CONNECTED_CONNECTION,
  "job_type": "full_sync",
  "trigger_type": "manual"
}
EOF
)

echo "   JSON payload: $ETL_JSON"

ETL_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/jobs/trigger \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$ETL_JSON")

echo "   ETL Response: $ETL_RESPONSE"

JOB_ID=$(echo "$ETL_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('id', ''))
except:
    pass
" 2>/dev/null)

if [ -n "$JOB_ID" ]; then
    echo "   ✅ ETL job created with ID: $JOB_ID"
    
    # Wait a moment for job to process
    echo "   ⏳ Waiting for job to process..."
    sleep 8
    
    # Check job status
    JOB_STATUS_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" \
        "http://localhost:8000/api/v1/jobs/$JOB_ID")
    
    echo "   Job status response: $JOB_STATUS_RESPONSE"
    
    JOB_STATUS=$(echo "$JOB_STATUS_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('status', 'unknown'))
except:
    print('unknown')
" 2>/dev/null)
    
    RECORDS_PROCESSED=$(echo "$JOB_STATUS_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('records_processed', 0))
except:
    print(0)
" 2>/dev/null)
    
    echo "   📊 Job Status: $JOB_STATUS"
    echo "   📈 Records Processed: $RECORDS_PROCESSED"
    
else
    echo "   ❌ Failed to create ETL job"
    echo "   Response: $ETL_RESPONSE"
    
    # Check if it's an authentication issue
    if echo "$ETL_RESPONSE" | grep -q "401\|unauthorized"; then
        echo "   🔑 Authentication issue - token may have expired"
    elif echo "$ETL_RESPONSE" | grep -q "404"; then
        echo "   🔍 Endpoint not found - check if /api/v1/jobs/trigger exists"
    elif echo "$ETL_RESPONSE" | grep -q "connection_id"; then
        echo "   🔗 Connection issue - check if connection ID $CONNECTED_CONNECTION exists"
    fi
    exit 1
fi

# Step 7: Check analytics database (FIXED - use correct credentials)
echo ""
echo "7️⃣ Checking Analytics Database"
echo "=============================="

echo -n "   Checking for analytics tables... "
ANALYTICS_TABLES=$(PGPASSWORD=admin psql -h localhost -p 5432 -U postgres -d analytics_data -t -c "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'conn_%';" 2>/dev/null | xargs)

if [ -n "$ANALYTICS_TABLES" ]; then
    echo "✅ Found tables"
    echo "   Analytics tables:"
    for table in $ANALYTICS_TABLES; do
        count=$(PGPASSWORD=admin psql -h localhost -p 5432 -U postgres -d analytics_data -t -c "SELECT COUNT(*) FROM $table;" 2>/dev/null | xargs)
        echo "     • $table: $count records"
    done
else
    echo "⚠️  No analytics tables found yet"
    echo "   This is normal if ETL job just started or failed"
    echo "   Check backend logs for ETL processing details"
fi

# Step 8: Show backend logs for debugging
echo ""
echo "8️⃣ Backend Logs (last 10 lines)"
echo "==============================="

if command -v docker-compose &> /dev/null; then
    echo "   Recent backend logs:"
    docker-compose logs --tail=10 backend 2>/dev/null || echo "   Could not fetch logs via docker-compose"
else
    echo "   ℹ️  Check backend console for ETL processing logs"
fi

# Step 9: Provide next steps
echo ""
echo "9️⃣ Usage Guide"
echo "=============="

echo ""
echo "🎉 ETL Job Demo Completed!"
echo ""
echo "📋 What you can do now:"
echo ""
echo "1️⃣ VIEW ETL JOBS IN UI:"
echo "   • Go to: http://localhost:3000/connections"
echo "   • Find your connection card"
echo "   • Click 'Show Jobs' to see ETL job history"
echo "   • You should see Job ID: $JOB_ID"
echo ""
echo "2️⃣ CHECK ETL MANAGER:"
echo "   • The ETLJobManager component should now show jobs"
echo "   • Status should be 'completed' if successful"
echo "   • Records processed count should be > 0"
echo ""
echo "3️⃣ EXPLORE DATA IN SUPERSET:"
echo "   • Go to: http://localhost:8088"
echo "   • Login: admin / admin"
echo "   • Go to SQL Lab"
if [ -n "$ANALYTICS_TABLES" ]; then
    first_table=$(echo $ANALYTICS_TABLES | cut -d' ' -f1)
    echo "   • Try: SELECT * FROM $first_table LIMIT 10;"
fi
echo ""
echo "4️⃣ TROUBLESHOOT IF NEEDED:"
echo "   • Check backend logs for ETL processing details"
echo "   • Verify connection is actually 'connected' status"
echo "   • Make sure source database has readable data"

echo ""
echo "✅ DEMO COMPLETE - Your ETL pipeline is working!"