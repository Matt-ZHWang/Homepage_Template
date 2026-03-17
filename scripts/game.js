var vue = new Vue({
    el: '#bbb',
    data: {
      
    },
    mounted() {
      // 监听页面的mouseleave事件，当鼠标移出浏览器页面可用区域 并 松开按键时，停止拖动
      document.addEventListener("mouseleave", (e) => {
        document.onmousemove = document.onmouseup = null;
      });
    },
    methods: {
      // 拖动效果
      handleMouseDown(e) {
        
        let box = document.getElementById('bbb');
        // box.style.cursor = move;
        // e.pageX, e.pageY 是鼠标在页面上的坐标
        // box.offsetLeft, box.offsetTop 是元素相对于页面左上角的偏移位置
        // disx, disy 便是鼠标相对于元素左上角的偏移位置
        let disx = e.pageX - box.offsetLeft;
        let disy = e.pageY - box.offsetTop;

        box.style.opacity = 0.5;

        // document.documentElement.clientWidth: 浏览器页面可用宽度
        // document.documentElement.clientHeight: 浏览器页面可用高度

        document.onmousemove = function (e) {       // 鼠标移动的时候计算元素的位置
          let x, y;
          // e.pageX - disx  鼠标在页面上的位置 - 鼠标在元素中的偏移位置  得到的是元素相对于页面左上角的偏移位置
          if ((e.pageX - disx) > 0) {  // 元素相对于页面左上角的偏移位置 大于0时
            if ((e.pageX - disx) > document.documentElement.clientWidth - 60) {   // 元素相对于页面左上角的偏移位置 移出到页面以外（右侧）
              x = document.documentElement.clientWidth - 60;   // 60是元素自身的宽高
            } else {
              x = e.pageX - disx;
            }
          } else {    // 元素移到到页面以外（左侧）
            x = 0;
          }

          if ((e.pageY - disy) > 0) {
            if ((e.pageY - disy) > document.documentElement.clientHeight - 60) {   // 元素移动到页面以外（底部）
              y = document.documentElement.clientHeight - 60;
            } else {
              y = e.pageY - disy;
            }
          } else {        // 元素移动到页面以外（顶部）
            y = 0;
          }

          box.style.left = x + 'px';
          box.style.top = y + 'px';


        }

      },
      // 释放鼠标按钮，将事件清空，否则始终会跟着鼠标移动
      handleMouseUp() {
        let box = document.getElementById('bbb');
        box.style.opacity = 1;

        document.onmousemove = document.onmouseup = null;

        
        let judge1 = document.getElementById('house');
        let judge2 = document.getElementById('ruin');
        

        let box_x = box.getBoundingClientRect().left;
        let box_y = box.getBoundingClientRect().top;
        let box_hei = box.getBoundingClientRect().height;

        let house_x = judge1.getBoundingClientRect().left;
        let house_wid = judge1.getBoundingClientRect().width;

        let ruin_x = judge2.getBoundingClientRect().left;
        let ruin_wid = judge2.getBoundingClientRect().width;
        let ruin_y  = judge2.getBoundingClientRect().top;

        


        if((box_x>house_x) && (box_x<(house_x+house_wid)) ){

            judge1.style.content = "url('judge_house_after.png')";
            alert("This house is EMPTY......");
          }
        // 判断房子1

        else if((box_x>ruin_x) && (box_x<(ruin_x+ruin_wid)) && ((box_y+box_hei)>ruin_y)){

            judge2.style.content = "url('judge_ruin_after.png')";
            alert("It's all RUINED.");
            document.getElementById("allruined").style.display = "block";
            document.getElementById("ruinplay").style.display = "block";
            // document.getElementById("escapebutton").style.display = "block";
          }
        // 判断房子1
      },
    },
  });

function forlover(){
    document.getElementById("escapebutton").innerText = "FOR LOVER."
}

function res(){
    document.getElementById("escapebutton").innerText = "BACK INDOOR."
}

function gotopage(){
    if(document.getElementById("ruinplay").style.display == "block"){
        alert("Time to go back.");
        window.location.href="4.html";
    }

    else{
        alert("No fear: No going back home.");
    }
}
