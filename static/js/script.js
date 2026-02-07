jQuery(document).ready(function(){

    $('body').on('click', '.menu-btn', function(){
          $(this).toggleClass('btnActive');
          if ($(this).hasClass('btnActive')){
              $('body').addClass('menuActive')
              //$('body').append('<div class="site-overlay">');
          }else{
              $('body').removeClass('menuActive')
          }
    });
      
    /*$('body').on('click', '.site-overlay', function(){
          $('body').removeClass('menuActive')
          $('.site-overlay').remove();
          $('.menu-btn').removeClass('btnActive');
    });*/

    $('.ctg__filter_remove').on('click', function(){
      $(this).parents('.ctg__filter_a').remove();
    });

    $('.raty').each(function(){
      var score = $(this).attr('data-score'),
        readonly = $(this).attr('data-readonly')
        $(this).append("<span class='score'>"+score+"</span>");
      $(this).raty({
            numberMax: 100,
            score:score,
            starHalf    : starHalfUrl,
            starOff     : starOffUrl,
            starOn      : starOnUrl,
            readOnly:readonly
        })    
    })  
    $('.owl-carousel').each(function(){
        var el = $(this);
        $(this).owlCarousel({
            loop:false,
            nav:true,
            dots:false,
            lazyLoad:true,
            items:1,
            margin:20,
            smartSpeed:800,
            autoplay:true,
            autoplayTimeout:7000,
            autoplayHoverPause:true,
            responsive:{
                991:{
                    items:3
                },
                767:{
                    items:3
                },
                480:{
                  items:2
                },
                220:{
                    items:1
                }
            },
            onInitialized:function(event){
                
            },
            onTranslated:function(event){
                
            }
        });
    });
    
    
    var scrollTicking = false;
    $(document).on('scroll', function(){
      if (!scrollTicking) {
        requestAnimationFrame(function(){
          if ($(document).scrollTop() > 80){
            $('body').addClass('headerFixed');
          }else{
            $('body').removeClass('headerFixed');
          }
          scrollTicking = false;
        });
        scrollTicking = true;
      }
    });
    
    

});

