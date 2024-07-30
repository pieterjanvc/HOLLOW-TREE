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

    if (document.getElementById(x.id)) {        
        hideShow(x.effect,document.getElementById(x.id));
        // Check for elements with a "for" attribute with the same ID (e.g. select box labels)
        if (document.querySelector('[for="' + x.id + '"]')) {
            hideShow(x.effect,document.querySelector('[for="' + x.id + '"]'));
        } 
    } else if (document.querySelector('[data-value="' + x.id + '"]')) {
        hideShow(x.effect,document.querySelector('[data-value="' + x.id + '"]'));
    } else {
        if (x.alertNotFound == true) {
            alert("No element found with an ID or data-value of:" + x.id);
        }        
        return;
    }  
    
});
