
$(document).ready(function(){


  // tweeet by ajax
  $("#tweet-form").submit(function(e){
    var text = $("textarea").val().length;
    if (text >= 140){
      alert("Please tweet within 140 words!");
      return false;
    }
    e.preventDefault();
    $.ajax({
      type: "POST",
      url: "/" + window.user + "/tweets/new",
      data: {
        "text":$("textarea").val()
      },
      success:function(d){
        console.log("tweeted success");
        window.location.reload();
      },
      error:function(e){
        console.log("tweeted error");
      }
    });
  });
  return false;
});




