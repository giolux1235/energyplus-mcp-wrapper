#!/bin/bash

# Get MCP Server URL for use in other projects

echo "🔗 EnergyPlus MCP Server URL Extractor"
echo "======================================"

# Check if we're in a cloud environment
if [ ! -z "$RAILWAY_STATIC_URL" ]; then
    MCP_URL="$RAILWAY_STATIC_URL"
    echo "🚂 Railway deployment detected"
elif [ ! -z "$FLY_APP_NAME" ]; then
    MCP_URL="https://$FLY_APP_NAME.fly.dev"
    echo "🛩️ Fly.io deployment detected"
elif [ ! -z "$HEROKU_APP_NAME" ]; then
    MCP_URL="https://$HEROKU_APP_NAME.herokuapp.com"
    echo "🟣 Heroku deployment detected"
elif [ ! -z "$VERCEL_URL" ]; then
    MCP_URL="https://$VERCEL_URL"
    echo "▲ Vercel deployment detected"
else
    # Local development
    MCP_URL="http://localhost:8080"
    echo "💻 Local development detected"
fi

echo ""
echo "🎯 MCP Server URL: $MCP_URL"
echo ""
echo "📋 Environment Variables for your other project:"
echo "MCP_SERVER_URL=$MCP_URL"
echo ""
echo "🔧 Add to your other project's environment:"
echo "export MCP_SERVER_URL=$MCP_URL"
echo ""
echo "📡 Test the MCP server:"
echo "curl $MCP_URL/status"
echo ""
echo "🛠️ Use in your other project:"
echo "const MCP_SERVER_URL = process.env.MCP_SERVER_URL || '$MCP_URL';"
echo ""

# Test the server
echo "🧪 Testing MCP server connection..."
if curl -s "$MCP_URL/status" > /dev/null; then
    echo "✅ MCP server is responding"
else
    echo "❌ MCP server is not responding"
fi
