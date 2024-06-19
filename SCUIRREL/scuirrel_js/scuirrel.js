// -----------------------------------
// ------ SCUIRREL JS FUNCTIONS ------
// ----------------------------------- 

// Shift + enter will send a message
$(document).keyup(function(event) {
    if ($("#chat-newChat").is(":focus") && (event.key == "Enter") && event.ctrlKey) {
        $("#chat-send").click();
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
    Shiny.setInputValue("chat-selectedMsg", JSON.stringify(flaggedMsg));            

}

// Make sure the custom Shiny input gets initialised
$(document).on('shiny:connected', function() {    
    Shiny.setInputValue("chat-selectedMsg", JSON.stringify(flaggedMsg)); 
});

Shiny.addCustomMessageHandler("progressBar", function(x) {

    var elem = document.getElementById(x.id);
    elem.style.width = x.percent + '%';

});

// When this function is called, the chat will scroll to the top of the .chatWindow class
Shiny.addCustomMessageHandler("scrollElement", function(x){
    var element = document.querySelector(x.selectors);
    // log all elements in x
    console.log(x);
    if (x.direction == "top") {
        element.scrollTop = 0;
        //print scroll to top to console
        console.log("scrolling to top");
    } else if (x.direction == "bottom") {
        element.scrollBottom = 0;
        console.log("scrolling to bottom");
    }
});
