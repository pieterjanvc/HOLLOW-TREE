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

$(document).on('shiny:connected', function(event) {
    let flaggedMsg = [];
    Shiny.setInputValue("selectedMsg", JSON.stringify(flaggedMsg)); 
    document.getElementById("report").addEventListener("click", function() {    
        var messages = document.querySelectorAll('.talk-bubble');    
        // Loop through each element and attach a click event listener
        messages.forEach(function(message) {
            message.addEventListener('click', function() {
            // Change its properties
            if (message.classList.contains('selectedMsg')){
                message.classList.remove('selectedMsg');
                flaggedMsg.splice(flaggedMsg.indexOf(message.getAttribute('msg')), 1);
            } else {
                message.classList.add('selectedMsg');
                flaggedMsg.push(message.getAttribute('msg'))
            }
            Shiny.setInputValue("selectedMsg", JSON.stringify(flaggedMsg));            
            });
        })
    });
});
