#!/bin/bash
# Test Admin Panel CRUD via API

echo "=== Admin Panel CRUD Test ==="
echo ""

# Setup
BASE_URL="http://localhost:8000/api"
TEST_ID=""

# 1. Test CREATE
echo "1️⃣ CREATE Test:"
RESPONSE=$(curl -s -X POST "$BASE_URL/persons" \
  -H "Content-Type: application/json" \
  -d '{
    "vorname": "AdminTest",
    "nachname": "Person",
    "email": "admin-test@test.local",
    "gremium": "TestGruppe",
    "aktiv": true
  }')

TEST_ID=$(echo "$RESPONSE" | grep -o '"id":[0-9]*' | cut -d: -f2)
echo "Created person with ID: $TEST_ID"
echo "Response: $RESPONSE"
echo ""

# 2. Test READ
echo "2️⃣ READ Test:"
curl -s -X GET "$BASE_URL/persons/$TEST_ID" | head -200
echo ""
echo ""

# 3. Test UPDATE (PATCH)
echo "3️⃣ UPDATE Test:"
RESPONSE=$(curl -s -X PATCH "$BASE_URL/persons/$TEST_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "gremium": "UpdatedGroup",
    "aktiv": false
  }')
echo "Updated person:"
echo "$RESPONSE"
echo ""

# 4. Test DELETE
echo "4️⃣ DELETE Test:"
curl -s -X DELETE "$BASE_URL/persons/$TEST_ID" -w "\nDelete status: %{http_code}\n"
echo ""

# 5. Verify DELETE
echo "5️⃣ Verify DELETE:"
curl -s -X GET "$BASE_URL/persons/$TEST_ID" -w "\nGet status: %{http_code}\n"
echo ""

echo "✅ Admin Panel CRUD Test Complete"
