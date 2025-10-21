#!/bin/bash

# EnergyPlus MCP HTTP Wrapper Deployment Script

echo "🚀 EnergyPlus MCP HTTP Wrapper Deployment Script"
echo "================================================"

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📦 Initializing Git repository..."
    git init
    git add .
    git commit -m "Initial commit: EnergyPlus MCP HTTP wrapper"
fi

echo ""
echo "Choose deployment platform:"
echo "1) Railway (Recommended - Easiest)"
echo "2) Fly.io"
echo "3) Docker"
echo "4) Just prepare files"

read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo "🚂 Deploying to Railway..."
        echo ""
        echo "Steps:"
        echo "1. Push to GitHub:"
        echo "   git remote add origin https://github.com/YOUR_USERNAME/energyplus-mcp-wrapper.git"
        echo "   git branch -M main"
        echo "   git push -u origin main"
        echo ""
        echo "2. Go to https://railway.app"
        echo "3. Click 'New Project' -> 'Deploy from GitHub repo'"
        echo "4. Select your repository"
        echo "5. Railway will auto-deploy!"
        echo ""
        echo "Your app will be available at: https://your-app-name.railway.app"
        ;;
    2)
        echo "🛩️ Deploying to Fly.io..."
        echo ""
        echo "Installing Fly CLI..."
        curl -L https://fly.io/install.sh | sh
        echo ""
        echo "Login to Fly.io:"
        echo "fly auth login"
        echo ""
        echo "Deploy:"
        echo "fly launch"
        echo "fly deploy"
        echo ""
        echo "Open your app:"
        echo "fly open"
        ;;
    3)
        echo "🐳 Building Docker image..."
        docker build -t energyplus-mcp .
        echo ""
        echo "To run locally:"
        echo "docker run -p 8080:8080 energyplus-mcp"
        echo ""
        echo "To deploy to cloud:"
        echo "1. Tag and push to Docker Hub:"
        echo "   docker tag energyplus-mcp YOUR_USERNAME/energyplus-mcp"
        echo "   docker push YOUR_USERNAME/energyplus-mcp"
        echo ""
        echo "2. Deploy to any Docker platform (AWS ECS, Google Cloud Run, etc.)"
        ;;
    4)
        echo "📁 Files prepared for deployment!"
        echo ""
        echo "Created files:"
        echo "✅ requirements.txt - Python dependencies"
        echo "✅ railway.json - Railway configuration"
        echo "✅ fly.toml - Fly.io configuration"
        echo "✅ Procfile - Heroku/other platforms"
        echo "✅ Dockerfile - Docker configuration"
        echo "✅ web-app.html - Sample web application"
        echo "✅ DEPLOYMENT.md - Detailed deployment guide"
        echo ""
        echo "Next steps:"
        echo "1. Push to GitHub"
        echo "2. Deploy to your chosen platform"
        echo "3. Update web-app.html with your deployed URL"
        ;;
    *)
        echo "❌ Invalid choice. Please run the script again."
        exit 1
        ;;
esac

echo ""
echo "🎉 Deployment preparation complete!"
echo ""
echo "📖 For detailed instructions, see DEPLOYMENT.md"
echo "🌐 For a sample web app, open web-app.html in your browser"
