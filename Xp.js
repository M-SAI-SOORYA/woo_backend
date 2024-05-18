const mongoose=require('mongoose');
const mongoURI="mongodb+srv://saisooryamarri:Hs8iRlr1mfhvMAKB@system.vesozdf.mongodb.net/?retryWrites=true&w=majority&appName=System"
mongoose.connect(mongoURI);
const xpSchema=new mongoose.Schema({
    gymXp:{
        type:Number,
        required:true
    },
    todoXp:{
        type:Number,
        required:true
    },
    dietXp:{
        type:Number,
        required:true
    },
    socialXp:{
        type:Number,
        required:true
    },
    dater:{
        type:String,
        required:true
    },
    title:{
        type:String,
        required:true
    },
    currentlevel:{
        type:Number,
        
        required:true
    },
    totalXp:{
        type:Number,
        required:true
    },
    rewards:{
        type:String,
        default:"No Rewards Right Now"
    },
    penalties:{
        type:String,
        default:"No Penalties Till Now"
    },
    job:{
        type:String,
        default:"No Job Right Now",
        required:true
        
    }


});
const xp=mongoose.model("xp",xpSchema);
module.exports=xp;