#!/bin/bash

# =================================================================
# GNB Dog Image Generation Backend - Database Setup Script
# =================================================================
# This script automates the database setup process

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DB_NAME="gnb_dog_images"
DB_USER="gnb_user"
DB_PASSWORD=""
DB_HOST="localhost"
DB_PORT="6543"
ADMIN_USER="postgres"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Function to check if PostgreSQL is running
check_postgres() {
    if ! command -v psql &> /dev/null; then
        print_error "PostgreSQL client (psql) not found. Please install PostgreSQL."
        exit 1
    fi
    
    if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" &> /dev/null; then
        print_error "PostgreSQL server is not running on $DB_HOST:$DB_PORT"
        exit 1
    fi
    
    print_status "PostgreSQL server is running"
}

# Function to prompt for database credentials
get_credentials() {
    echo
    print_step "Database Configuration"
    echo "Please provide the following information:"
    
    read -p "Database name [$DB_NAME]: " input_db_name
    DB_NAME=${input_db_name:-$DB_NAME}
    
    read -p "Database user [$DB_USER]: " input_db_user
    DB_USER=${input_db_user:-$DB_USER}
    
    read -s -p "Database password (will be created): " DB_PASSWORD
    echo
    
    read -p "Database host [$DB_HOST]: " input_db_host
    DB_HOST=${input_db_host:-$DB_HOST}
    
    read -p "Database port [$DB_PORT]: " input_db_port
    DB_PORT=${input_db_port:-$DB_PORT}
    
    read -p "PostgreSQL admin user [$ADMIN_USER]: " input_admin_user
    ADMIN_USER=${input_admin_user:-$ADMIN_USER}
    
    echo
}

# Function to create database and user
create_database() {
    print_step "Creating database and user"
    
    # Create user and database
    PGPASSWORD="" psql -h "$DB_HOST" -p "$DB_PORT" -U "$ADMIN_USER" -d postgres << EOF
-- Create user if not exists
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
        CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD';
    END IF;
END
\$\$;

-- Create database if not exists
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER;'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

    if [ $? -eq 0 ]; then
        print_status "Database and user created successfully"
    else
        print_error "Failed to create database and user"
        exit 1
    fi
}

# Function to run DDL script
create_tables() {
    print_step "Creating tables and schema"
    
    # Check if DDL file exists
    if [ ! -f "create_tables.sql" ]; then
        print_error "create_tables.sql not found in current directory"
        exit 1
    fi
    
    # Run the DDL script
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f create_tables.sql
    
    if [ $? -eq 0 ]; then
        print_status "Tables created successfully"
    else
        print_error "Failed to create tables"
        exit 1
    fi
}

# Function to generate connection string
generate_connection_string() {
    print_step "Generating connection string"
    
    CONNECTION_STRING="postgresql+asyncpg://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
    
    echo
    print_status "Database setup completed!"
    echo
    echo "Add this to your .env file:"
    echo "DATABASE_URL=$CONNECTION_STRING"
    echo
    
    # Optionally write to .env file
    read -p "Would you like to update .env file automatically? (y/N): " update_env
    if [[ $update_env =~ ^[Yy]$ ]]; then
        if [ -f ".env" ]; then
            # Update existing .env file
            if grep -q "^DATABASE_URL=" .env; then
                sed -i.bak "s|^DATABASE_URL=.*|DATABASE_URL=$CONNECTION_STRING|" .env
                print_status "Updated DATABASE_URL in .env file"
            else
                echo "DATABASE_URL=$CONNECTION_STRING" >> .env
                print_status "Added DATABASE_URL to .env file"
            fi
        else
            print_warning ".env file not found. Please create one manually."
        fi
    fi
}

# Function to test connection
test_connection() {
    print_step "Testing database connection"
    
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT COUNT(*) FROM image_generations;" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        print_status "Database connection test successful"
    else
        print_warning "Database connection test failed, but setup may still be correct"
    fi
}

# Main execution
main() {
    echo "========================================"
    echo "GNB Dog Image Generation - Database Setup"
    echo "========================================"
    echo
    
    print_step "Checking PostgreSQL availability"
    check_postgres
    
    get_credentials
    create_database
    create_tables
    generate_connection_string
    test_connection
    
    echo
    print_status "Setup completed successfully!"
    echo
    echo "Next steps:"
    echo "1. Update your .env file with the DATABASE_URL"
    echo "2. Install Python dependencies: pip install -r requirements.txt"
    echo "3. Run your FastAPI application: python main.py"
    echo
}

# Script help
show_help() {
    echo "GNB Dog Image Generation - Database Setup Script"
    echo
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -h, --help    Show this help message"
    echo "  --auto        Run with default values (requires manual .env update)"
    echo
    echo "This script will:"
    echo "1. Check PostgreSQL availability"
    echo "2. Create database and user"
    echo "3. Run DDL script to create tables"
    echo "4. Generate connection string"
    echo "5. Optionally update .env file"
    echo
}

# Parse command line arguments
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    --auto)
        print_warning "Running in automatic mode with defaults"
        check_postgres
        create_database
        create_tables
        generate_connection_string
        test_connection
        ;;
    *)
        main
        ;;
esac 