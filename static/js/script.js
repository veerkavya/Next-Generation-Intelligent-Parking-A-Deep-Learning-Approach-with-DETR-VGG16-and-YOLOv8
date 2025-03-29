// Update digital clock
function updateClock() {
    const now = new Date();
    const time = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const date = now.toLocaleDateString([], { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    document.getElementById('digital-clock').textContent = `${time} | ${date}`;
  }
  
  // Get the total number of slots from the database on initial load
  let totalSlots = 32; // Default value, will be updated based on actual data
  
  // Initialize the parking layout
  function initializeParkingLayout() {
    const layout = document.getElementById('parking-layout');
    
    // Start with the floor divider
    layout.innerHTML = '<div class="floor-divider">Ground Floor</div>';
    
    // Create the parking spots
    for (let i = 1; i <= totalSlots; i++) {
      const spot = document.createElement('div');
      spot.className = 'parking-spot';
      spot.id = `spot-${i}`;
      spot.innerHTML = `${i}`;
      layout.appendChild(spot);
    }
  }
  
  // Keep track of previous slot data to detect changes
  let previousSlotData = null;
  let currentAssignedSpot = null;
  
  // Function to fetch slot data and update the page
  function fetchSlots() {
    fetch("/api/slots")
      .then(response => response.json())
      .then(data => {
        // Calculate total slots if not set yet
        if (!previousSlotData) {
          const allSlots = [
            ...data.free_slots,
            ...data.occupied_slots,
            ...data.waiting_slots
          ];
          
          // Find the highest slot number to determine total
          if (allSlots.length > 0) {
            totalSlots = Math.max(...allSlots.map(slot => slot[0]));
            // Reinitialize layout with correct number of slots
            initializeParkingLayout();
          }
        }
        
        // Update counters
        document.getElementById("free-count").textContent = data.free_slots.length;
        document.getElementById("occupied-count").textContent = data.occupied_slots.length;
        document.getElementById("waiting-count").textContent = data.waiting_slots.length;
  
        // Update the parking spots UI
        updateParkingSpots(data);
  
        // Handle new assignments
        detectNewAssignments(data);
  
        // Store current data for next comparison
        previousSlotData = JSON.parse(JSON.stringify(data));
  
        // Update the last updated time
        const lastUpdated = document.getElementById("last-updated");
        const now = new Date();
        lastUpdated.textContent = `Last updated: ${now.toLocaleString()}`;
      })
      .catch(error => {
        console.error("Error fetching slots:", error);
      });
  }
  
  // Function to update the parking spots UI based on data
  function updateParkingSpots(data) {
    // Reset all spots first
    for (let i = 1; i <= totalSlots; i++) {
      const spot = document.getElementById(`spot-${i}`);
      if (spot) {
        spot.className = 'parking-spot';
        spot.innerHTML = `${i}`;
      }
    }
  
    // Update free spots
    data.free_slots.forEach(slot => {
      const spotId = slot[0];
      const spot = document.getElementById(`spot-${spotId}`);
      if (spot) {
        spot.className = 'parking-spot available';
        spot.innerHTML = `${spotId}`;
      }
    });
  
    // Update occupied spots
    data.occupied_slots.forEach(slot => {
      const spotId = slot[0];
      const licensePlate = slot[2] || '';
      const spot = document.getElementById(`spot-${spotId}`);
      if (spot) {
        spot.className = 'parking-spot occupied';
        spot.innerHTML = `${spotId}${licensePlate ? `<div class="license-tag">${licensePlate}</div>` : ''}`;
      }
    });
  
    // Update waiting spots
    data.waiting_slots.forEach(slot => {
      const spotId = slot[0];
      const licensePlate = slot[2] || '';
      const spot = document.getElementById(`spot-${spotId}`);
      if (spot) {
        spot.className = 'parking-spot waiting';
        spot.innerHTML = `${spotId}${licensePlate ? `<div class="license-tag">${licensePlate}</div>` : ''}`;
      }
    });
  }
  
  // Detect newly assigned spots (for the "Go To" feature)
  function detectNewAssignments(data) {
    if (!previousSlotData) return;
    
    // Look for slots that were free before but are now waiting
    data.waiting_slots.forEach(slot => {
      const spotId = slot[0];
      const licensePlate = slot[2] || '';
      
      // Check if this spot was free before
      const wasFreeBefore = previousSlotData.free_slots.some(s => s[0] === spotId);
      
      if (wasFreeBefore) {
        showAssignment(spotId, licensePlate);
      }
    });
  }
  
  // Show assignment in the "Go To" section
  function showAssignment(spotId, licensePlate) {
    const assignedSpot = document.getElementById('assigned-spot');
    const directions = document.getElementById('directions');
    
        // Update to show both spot number and license plate
        assignedSpot.innerHTML = `
        <div class="assigned-spot-details">
            <div class="spot-number">${spotId}</div>
            <div class="license-plate">${licensePlate || 'N/A'}</div>
        </div>
    `;
        // Update directions to include vehicle number
        directions.textContent = licensePlate 
        ? `Vehicle ${licensePlate}, please proceed to spot ${spotId} on the Ground Floor.`
        : `Please proceed to spot ${spotId} on the Ground Floor.`;
    // Highlight the assigned spot on the map
    const spot = document.getElementById(`spot-${spotId}`);
    if (spot) {
      spot.classList.add('spotlight');
      
      // Remove spotlight after 1 minute
      setTimeout(() => {
        spot.classList.remove('spotlight');
      }, 60000);
    }
    
    // Store the current assignment
    currentAssignedSpot = spotId;
  }
  
  // Initialize the app when the page loads
  document.addEventListener("DOMContentLoaded", function() {
    // Start the clock and update every second
    updateClock();
    setInterval(updateClock, 1000);
    
    // Initialize the layout
    initializeParkingLayout();
    
    // Fetch initial data from the server
    fetchSlots();
    
    // Set placeholder for assigned spot
    const assignedSpot = document.getElementById('assigned-spot');
    assignedSpot.innerHTML = '<span class="assigned-spot-empty">Waiting for assignment...</span>';
    
    // Auto-refresh every 5 seconds
    setInterval(fetchSlots, 5000);
  });