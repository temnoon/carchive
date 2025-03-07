#!/bin/bash
# Combined script to manage both API and GUI servers on ports 8000/8001
# This is the standardized server management script

# Function to check if a port is in use
port_in_use() {
  lsof -i:$1 >/dev/null 2>&1
  return $?
}

# Function to stop a server on a specified port
stop_server() {
  local PORT=$1
  local SERVER_TYPE=$2
  
  echo "Stopping $SERVER_TYPE server on port $PORT..."
  if port_in_use $PORT; then
    # Find and kill processes using this port
    PID=$(lsof -t -i:$PORT)
    if [ ! -z "$PID" ]; then
      echo "Killing process $PID using port $PORT"
      kill $PID
      # Give it a moment to terminate
      sleep 1
      # Force kill if still running
      if ps -p $PID > /dev/null; then
        echo "Force killing process $PID"
        kill -9 $PID 2>/dev/null
      fi
    fi
  else
    echo "No $SERVER_TYPE server running on port $PORT"
  fi
}

# Parse command line arguments
COMMAND=${1:-"status"}
API_PORT=8000
GUI_PORT=8001
API_HOST="localhost"
GUI_HOST="localhost"
DEBUG=0

# Process based on command
case "$COMMAND" in
  start)
    # Check if servers are already running
    if port_in_use $API_PORT; then
      echo "Warning: Something is already using port $API_PORT"
      echo "Stop it first or use different ports"
      exit 1
    fi
    
    if port_in_use $GUI_PORT; then
      echo "Warning: Something is already using port $GUI_PORT"
      echo "Stop it first or use different ports"
      exit 1
    fi
    
    # Start API server
    echo "Starting API server on port $API_PORT..."
    ./run_api_8000.sh &
    API_PID=$!
    
    # Give API server time to start
    sleep 2
    
    # Start GUI server
    echo "Starting GUI server on port $GUI_PORT..."
    ./run_gui_8001.sh &
    GUI_PID=$!
    
    echo ""
    echo "Servers started successfully!"
    echo "API server: http://$API_HOST:$API_PORT"
    echo "GUI server: http://$GUI_HOST:$GUI_PORT"
    echo ""
    echo "You can access the web interface by opening http://$GUI_HOST:$GUI_PORT in your browser."
    ;;
    
  stop)
    # Stop both servers
    stop_server $API_PORT "API"
    stop_server $GUI_PORT "GUI"
    echo "Servers stopped"
    ;;
    
  restart)
    # Stop both servers
    "$0" stop
    
    # Wait a moment
    sleep 2
    
    # Start both servers
    "$0" start
    ;;
    
  status)
    # Check API server
    if port_in_use $API_PORT; then
      API_PID=$(lsof -t -i:$API_PORT)
      echo "API server is RUNNING on port $API_PORT (PID: $API_PID)"
    else
      echo "API server is NOT RUNNING on port $API_PORT"
    fi
    
    # Check GUI server
    if port_in_use $GUI_PORT; then
      GUI_PID=$(lsof -t -i:$GUI_PORT)
      echo "GUI server is RUNNING on port $GUI_PORT (PID: $GUI_PID)"
    else
      echo "GUI server is NOT RUNNING on port $GUI_PORT"
    fi
    ;;
    
  *)
    echo "Usage: $0 {start|stop|restart|status}"
    echo ""
    echo "Commands:"
    echo "  start    Start both API and GUI servers"
    echo "  stop     Stop both servers"
    echo "  restart  Restart both servers"
    echo "  status   Show server status (default)"
    exit 1
    ;;
esac

exit 0