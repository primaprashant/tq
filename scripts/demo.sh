#!/bin/zsh

# Terminal Size Settings
TERM_WIDTH=80
TERM_HEIGHT=24

# Create functions outside of the asciinema recording command
cat > demo_functions.zsh << 'EOF'
# Function to simulate typing at a moderate speed
type_text() {
    text="$1"
    for (( i=1; i<=${#text}; i++ )); do
        echo -n "${text[i]}"
        sleep 0.05
    done
    echo
}

# Function to execute commands with a typing simulation and delay
execute_command() {
    # Show prompt
    echo -ne "❯ "
    
    # Simulate typing the command
    type_text "$1"
    
    # Small pause after typing before execution
    sleep 0.5
    
    # Execute the command
    eval "$1"
    
    # Pause after execution
    echo ""
    sleep 1.5
}

# Function to show section headers
show_section() {
    echo -e "\n# $1"
    sleep 1
}
EOF

# Check if asciinema is installed
if ! command -v asciinema &> /dev/null; then
    echo "asciinema is not installed. Please install it first with:"
    echo "pip install asciinema"
    exit 1
fi

# Create a script file for the recording session
cat > demo_script.zsh << 'EOF'
#!/bin/zsh
source demo_functions.zsh

# Clear the screen for a clean start
clear

# Introduction
echo -e "# tqu - A Minimal CLI for Queue-Based Task Tracking"
sleep 2

# Installation section
show_section "Installation"
execute_command "uv tool install tqu"

# Basic usage (single queue mode)
show_section "Single Queue Mode"

show_section "Let's add some tasks"
execute_command "tqu add \"escape Helgen with Ralof or Hadvar\""

show_section "Let's check all the tasks added so far"
execute_command "tqu list"

show_section "Let's remove the most recently added task cause we already finished it"
execute_command "tqu pop"
execute_command "tqu list"

execute_command "tqu add \"talk to Jarl Balgruuf about the dragon\""
execute_command "tqu add \"learn Fus Ro Dah from the Greybeards\""
execute_command "tqu list"

show_section "Let's remove the oldest task that was added"
execute_command "tqu popfirst"
execute_command "tqu list"

# Advanced usage (multiple queue mode)
show_section "Multiple Queue Mode"

show_section "Let's add some tasks to \"thieves guild\" and \"civil war\" queues"
execute_command "tqu add \"talk to Brynjolf in Riften\" \"thieves guild\""
execute_command "tqu add \"steal sweetroll from the Jarl's table\" \"thieves guild\""
execute_command "tqu add \"choose between Imperials or Stormcloaks\" \"civil war\""

show_section "Let's check all the available queues"
execute_command "tqu"

show_section "Let's check the tasks in the \"civil war\" queue"
execute_command "tqu list \"civil war\""

execute_command "tqu pop \"civil war\""
execute_command "tqu list \"civil war\""

execute_command "tqu list \"thieves guild\""

show_section "Let's remove a task from the \"thieves guild\" queue using its id"
execute_command "tqu delete 4"
execute_command "tqu list \"thieves guild\""

show_section "Let's delete all the tasks in the \"thieves guild\" queue"
execute_command "tqu delete \"thieves guild\""
execute_command "tqu list \"thieves guild\""

execute_command "tqu"

# Conclusion
echo -e "# Visit https://github.com/primaprashant/tqu for more information"
sleep 3
EOF

# Make the script executable
chmod +x demo_script.zsh

# Start recording with fixed terminal size
echo "Starting demo recording with terminal size ${TERM_WIDTH}x${TERM_HEIGHT}..."
asciinema rec demo.cast --cols $TERM_WIDTH --rows $TERM_HEIGHT -c "./demo_script.zsh"

# Clean up the temporary files
rm demo_functions.zsh demo_script.zsh

echo "Recording completed! The recording has been saved as demo.cast"