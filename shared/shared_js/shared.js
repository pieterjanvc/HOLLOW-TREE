// ---------------------------------
// ------ SHARED JS FUNCTIONS ------
// --------------------------------- 

// Function to hide/show/enable/disable elements

function hideShow(x, element) {
    switch (x) {
        case "d":
            element.setAttribute("disabled", true);
            break;
        case "e":
            element.removeAttribute("disabled");
            break;
        case "h":
            element.style.display = "none";
            break;
        case "s":
            element.style.display = "";
            break;
        default:
            alert("Invalid effect: " + x +
                ". Use 'd' to disable, 'e' to enable, 'h' to hide, or 's' to show.");
    }
}

Shiny.addCustomMessageHandler("hideShow", function(x) {

    // Loop through each element in the array x.id and x.effect
    for (var i = 0; i < x.id.length; i++) {
        // Check if the element has an ID
        if (document.getElementById(x.id[i])) {
            hideShow(x.effect[i], document.getElementById(x.id[i]));
            // Check for elements with a "for" attribute with the same ID (e.g. select box labels)
            if (document.querySelector('[for="' + x.id[i] + '"]')) {
                hideShow(x.effect[i], document.querySelector('[for="' + x.id[i] + '"]'));
            }
        } else if (document.querySelector('[data-value="' + x.id[i] + '"]')) {
            hideShow(x.effect[i], document.querySelector('[data-value="' + x.id[i] + '"]'));
        } else {
            if (x.alertNotFound == true) {
                alert("No element found with an ID or data-value of:" + x.id[i]);
            }
            return;
        }
    }   
    
});
