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

Shiny.addCustomMessageHandler("progressBar", function(x) {

    var elem = document.getElementById(x.id);
    elem.style.width = x.percent + '%';
    
});

// document.getElementById("myElement").addEventListener("click", function() {
//     var element = document.getElementById("myElement");
//     if (element.classList.contains("myClass")) {
//         element.classList.remove("myClass");
//     } else {
//         element.classList.add("myClass");
//     }
// });
