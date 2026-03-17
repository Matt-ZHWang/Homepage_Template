let wINdo = [ "Architecture.", "Cold Bauhaus." , "Tear apart.", "Break down.", "Depress all.", "Could not fix.", "Go away.", "IDK.", "Faces and faces"]
  function myFunction(){
    document.getElementById("helloclickme").innerHTML = wINdo[Math.floor(Math.random() * wINdo.length)];
  }

  let conversation = [ ".....","???","——————","___",".............","___??....","???????//?" ]

  function myFunction(){
    document.getElementById("helloclickme").innerHTML = wINdo[Math.floor(Math.random() * wINdo.length)];
  }
  
// function changeBG(){
//   document.body.style.backgroundImage = "url('bg2.png')";
// }

// function resBG(){
//   document.body.style.backgroundImage = "url('fm.png')";
// }


function changeText(){
  document.getElementById("hug").innerHTML = wINdo[Math.floor(Math.random() * wINdo.length)];
}

function textapp(){
  document.getElementById("welcometo").style.display = "block";
}

function textdisapp(){
  document.getElementById("welcometo").style.display = "none";
}

var count = 0;

function changeTalk(){

  document.getElementById("dialogue1").innerHTML = conversation[Math.floor(Math.random() * conversation.length)];
  document.getElementById("dialogue2").innerHTML = conversation[Math.floor(Math.random() * conversation.length)];

  count++;

  if(count==5){
    //  alert("You can't get them TALK MORE.");
     document.getElementById("talk_alert").style.display = "block";
  }


  if(count==6){
    document.getElementById("escape").style.display = "block";
    document.getElementById("voice").play();

    document.getElementById("fan_alert").style.opacity = "0.1";
    document.getElementById("talk_alert").style.opacity = "0.1";
    document.getElementById("fanclose").style.opacity = "0.1";
    document.getElementById("fangif").style.opacity = "0.1";
    document.getElementById("dialogue1").style.opacity = "0.1";
    document.getElementById("dialogue2").style.opacity = "0.1";
    document.getElementById("talk").style.opacity = "0.1";
    document.getElementById("talkman").style.opacity = "0.1";
    document.getElementById("talkwoman").style.opacity = "0.1";

  }

}

function cannotturn(){
  //  alert("You CANNOT hide from it.")
  document.getElementById("fan_alert").style.display = "block";
}



