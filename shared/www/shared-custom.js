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

// Shift + enter will send a message
$(document).keyup(function(event) {
    if ($("#newChat").is(":focus") && (event.key == "Enter") && event.ctrlKey) {
        $("#send").click();
    }
});

// Selecting messages for reporting issues
let flaggedMsg = []; // keep list of selected messages

// This function is added to each message and executed when clicked
function chatSelection(message, x){

    // Toggle the background color to indicate selection
    if (message.classList.contains('selectedMsg')){
        message.classList.remove('selectedMsg');
        flaggedMsg.splice(flaggedMsg.indexOf(x), 1);
    } else {
        message.classList.add('selectedMsg');
        flaggedMsg.push(x)
    }
    // Keep track of selected messages in Shiny with custom input
    Shiny.setInputValue("selectedMsg", JSON.stringify(flaggedMsg));            

}

// Make sure the custom Shiny input gets initialised
$(document).on('shiny:connected', function() {    
    Shiny.setInputValue("selectedMsg", JSON.stringify(flaggedMsg)); 
});

Shiny.addCustomMessageHandler("progressBar", function(x) {

    var elem = document.getElementById(x.id);
    elem.style.width = x.percent + '%';

});
