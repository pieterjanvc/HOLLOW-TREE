// ---------------------------------
// ------ CUSTOM JS FUNCTIONS ------
// --------------------------------- 

// Function to hide/show/enable/disable elements
Shiny.addCustomMessageHandler("hideShow", function(x) {

    if (document.getElementById(x.id)) {
        var element = document.getElementById(x.id);
    } else if (document.querySelector('[data-value="' + x.id + '"]')) {
        var element = document.querySelector('[data-value="' + x.id + '"]');
    } else {
        alert("No element found with an ID or data-value of:" + x.id);
        return;
    }

    switch(x.effect) {
        case "d":
            element.setAttribute("disabled", true);
            break;
        case "e":
            element.setAttribute("disabled", false);
            break;
        case "h":
            element.style.display = "none";
            break;
        case "s":
            element.style.display = "";
            break;
    }
    
});

