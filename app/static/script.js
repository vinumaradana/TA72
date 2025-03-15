// Logout function
function logout() {
    fetch("/logout", {
        method: "POST",
        credentials: "include"
    }).then(response => {
        if (response.ok) {
            window.location.href = "/login";
        }
    });
}

// Handle login form submission
document.getElementById("loginForm")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    fetch("/login", {
        method: "POST",
        body: formData,
        credentials: "include"
    }).then(response => {
        if (response.ok) {
            window.location.href = "/dashboard";
        } else {
            response.json().then(data => {
                const errorMessage = document.getElementById("error-message");
                errorMessage.textContent = data.detail;
            });
        }
    });
});

// Handle signup form submission
document.getElementById("signupForm")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    fetch("/signup", {
        method: "POST",
        body: formData,
        credentials: "include"
    }).then(response => {
        if (response.ok) {
            // Check if response is a redirect
            if (response.redirected) {
                window.location.href = response.url;
            } else {
                // Handle the response manually
                response.json().then(data => {
                    alert("Successfully Registered!!!");
                    window.location.href = "/login";
                });
            }
        } else {
            response.json().then(data => {
                alert(data.detail || "Signup failed");
            });
        }
    }).catch(error => {
        console.error("Error:", error);
        alert("An error occurred during signup");
    });
});

// Fetch and display devices
function fetchDevices() {
    fetch("/devices", { credentials: "include" })
        .then(response => {
            if (response.ok) {
                return response.json();
            } else {
                return response.json().then(err => {
                    throw new Error(err.detail || "Failed to fetch devices");
                });
            }
        })
        .then(data => {
            const deviceList = document.getElementById("device-list");
            deviceList.innerHTML = ""; // Clear the list
            data.forEach(device => {
                const li = document.createElement("li");
                li.textContent = `Device ID: ${device.device_id}`;
                deviceList.appendChild(li);
            });
        })
        .catch(error => {
            console.error(error);
            alert(error.message);
        });
}
// Fetch and display wardrobe items
function fetchWardrobe() {
    fetch("/api/wardrobe", {
        credentials: "include"
    })
    .then(response => {
        if (response.ok) {
            return response.json();
        } else {
            return response.json().then(err => {
                throw new Error(err.detail || "Failed to fetch wardrobe items");
            });
        }
    })
    .then(data => {
        const wardrobeList = document.getElementById("wardrobe-list");
        if (!wardrobeList) return; // Only proceed if we're on the wardrobe page
        
        wardrobeList.innerHTML = ""; // Clear the list

        // Loop through the data and create list items
        data.forEach(item => {
            const li = document.createElement("li");
            li.textContent = `${item.item_name} (${item.item_type})`;
            wardrobeList.appendChild(li);
        });
    })
    .catch(error => {
        console.error(error);
        alert(error.message); // Show error message
    });
}

// Add event listeners for forms
document.addEventListener("DOMContentLoaded", () => {
    // Add item form
    document.getElementById("add-clothing-form")?.addEventListener("submit", (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        fetch("/add-item", {
            method: "POST",
            body: formData,
            credentials: "include"
        })
        .then(response => {
            if (response.ok) {
                return response.json();
            } else {
                return response.json().then(err => {
                    throw new Error(err.detail || "Failed to add item");
                });
            }
        })
        .then(data => {
            alert(data.message);
            fetchWardrobe(); // Refresh the wardrobe list
        })
        .catch(error => {
            alert(error.message);
        });
    });

    // Register device form
    document.getElementById("register-device-form")?.addEventListener("submit", (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        fetch("/register-device", {
            method: "POST",
            body: formData,
            credentials: "include"
        })
        .then(response => {
            if (response.ok) {
                return response.json();
            } else {
                return response.json().then(err => {
                    throw new Error(err.detail || "Failed to register device");
                });
            }
        })
        .then(data => {
            alert(data.message);
            fetchDevices(); // Refresh the device list
        })
        .catch(error => {
            alert(error.message);
        });
    });

    // Fetch devices and wardrobe items on page load
    if (document.getElementById("device-list")) {
        fetchDevices();
    }
    if (document.getElementById("wardrobe-list")) {
        fetchWardrobe();
    }
});