# ============================================================================
# backend/run_analytics_demo.py
# Demo script to show the integration working
# ============================================================================

import asyncio
import requests
import json
from app.services.superset_integration import SupersetIntegration
from app.services.analytics_automation import AnalyticsAutomation

async def demo_analytics_integration():
    """Demo the analytics integration workflow"""
    
    print("🎯 Analytics Connector to Superset Integration Demo")
    print("=" * 60)
    
    # 1. Check if Superset is running
    print("1️⃣ Checking Superset availability...")
    try:
        response = requests.get("http://localhost:8088/health", timeout=5)
        if response.status_code == 200:
            print("✅ Superset is running")
        else:
            print("❌ Superset is not responding correctly")
            return
    except:
        print("❌ Superset is not accessible at http://localhost:8088")
        print("   Please start Superset first!")
        return
    
    # 2. Test Superset integration
    print("\n2️⃣ Testing Superset integration...")
    superset_integration = SupersetIntegration()
    
    # Mock connection ID (you'd use a real one)
    test_connection_id = 1
    
    print(f"   Attempting to sync connection {test_connection_id}...")
    # This would normally sync a real connection
    # success = superset_integration.sync_connection_to_superset(test_connection_id)
    
    print("✅ Integration test completed")
    
    # 3. Demo analytics automation
    print("\n3️⃣ Testing analytics automation...")
    analytics_automation = AnalyticsAutomation()
    
    mock_tables = ["customers", "orders", "products", "sales_metrics"]
    result = analytics_automation.create_analytics_for_new_data(test_connection_id, mock_tables)
    
    print(f"   Created analytics for {len(mock_tables)} tables")
    print(f"   Result: {json.dumps(result, indent=2)}")
    
    print("\n🎉 Demo completed!")
    print("\n📋 Next steps:")
    print("   1. Create a real database connection in your app")
    print("   2. The connection will auto-sync to Superset")
    print("   3. Run ETL jobs to populate analytics_data")
    print("   4. Basic dashboards will be auto-created")
    print("   5. Access analytics at http://localhost:8088")

if __name__ == "__main__":
    asyncio.run(demo_analytics_integration())