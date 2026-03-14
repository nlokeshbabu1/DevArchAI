#!/bin/bash
# Test script for report export functionality

echo "========================================"
echo "DevArchAI Report Export Test"
echo "========================================"
echo ""

# Check if backend is running
echo "1. Checking backend status..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ Backend is running on port 8000"
else
    echo "   ❌ Backend is not responding"
    exit 1
fi

# Check packages
echo ""
echo "2. Checking required packages..."
source /home/lokesh/.ai-engine/bin/activate
python -c "import openpyxl; print('   ✅ openpyxl:', openpyxl.__version__)"
python -c "import reportlab; print('   ✅ reportlab:', reportlab.__version__)"
python -c "import xlsxwriter; print('   ✅ xlsxwriter:', xlsxwriter.__version__)"

echo ""
echo "3. Testing export endpoints..."
echo ""
echo "   To test exports, use these curl commands:"
echo ""
echo "   # PDF Export:"
echo "   curl -H 'Authorization: Bearer YOUR_TOKEN' \\"
echo "     'http://localhost:8000/api/v1/reports/REPORT_ID/download?format=pdf' \\"
echo "     -o report.pdf"
echo ""
echo "   # Excel Export:"
echo "   curl -H 'Authorization: Bearer YOUR_TOKEN' \\"
echo "     'http://localhost:8000/api/v1/reports/REPORT_ID/download?format=xlsx' \\"
echo "     -o report.xlsx"
echo ""
echo "   # JSON Export:"
echo "   curl -H 'Authorization: Bearer YOUR_TOKEN' \\"
echo "     'http://localhost:8000/api/v1/reports/REPORT_ID/download?format=json' \\"
echo "     -o report.json"
echo ""
echo "   # CSV Export:"
echo "   curl -H 'Authorization: Bearer YOUR_TOKEN' \\"
echo "     'http://localhost:8000/api/v1/reports/REPORT_ID/download?format=csv' \\"
echo "     -o report.csv"
echo ""
echo "========================================"
echo "Backend Status: RUNNING"
echo "Export Formats: PDF, XLSX, JSON, CSV"
echo "========================================"
