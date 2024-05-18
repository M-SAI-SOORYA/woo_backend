const express = require('express')
const app = express()
const port = 5000
const cors = require("cors");

app.use(cors());

const Xp = require("../backend/models/Xp.js");

app.use(express.json());

app.get('/get/item1', async (req, res) => {
    try {
        const item1 = await Xp.findById("664632b48435b33dc80620e0");
        res.json(item1);
    } catch (err) {
        res.status(500).send(err);
    }
});

app.get('/get/items', async (req, res) => {
    try {
        const items = await Xp.find();
        res.json(items);
    } catch (err) {
        res.status(500).send(err);
    }
});
app.post('/xp', async (req, res) => {
    try {
        // Extract XP data from the request body.

        const { gymXp, todoXp, dietXp, socialXp } = req.body;

        // Get the current date in "dd-mm-yyyy" format
        const now = new Date();

        const day = String(now.getDate()).padStart(2, '0');
        const month = String(now.getMonth() + 1).padStart(2, '0'); // January is 0!
        const year = now.getFullYear();
        const dater = `${day}-${month}-${year}`;

        const totalXp = gymXp + todoXp + dietXp + socialXp;
        const getPenalties = (gymXp, todoXp, dietXp, socialXp) => {
            if ([gymXp, todoXp, dietXp, socialXp].includes(-5)) {
                const penalties = [
                    "No social media for 2 days, full focus mode",
                    "No hearing songs for 2 days",
                    "Solve Leetcode 10 medium-level problems"
                ];
                return penalties[Math.floor(Math.random() * penalties.length)];
            }
            return "No Penalties Till Now";
        };

        const getReward = (totalXp) => {
            const level = getCurrentLevel(totalXp);
            if (level % 3 === 0 && level !== 0) {
                const rewards = [
                    "Watching Netflix Series",
                    "Hanging out with friends",
                    "Buying Good clothes"
                ];
                return rewards[Math.floor(Math.random() * rewards.length)];
            }
            return "No Rewards Right Now";
        };
        const getCurrentLevel = (totxp) => {
            const xpPerLevel = 100;

            // Calculate the current level
            const level = Math.floor(totxp / xpPerLevel);

            return level;

        }
        const getTitle = (level) => {
            if (level < 10) {
                return "Beginner";
            }
            else if (level >= 10 && level < 20) {
                return "Iron Warrior";
            }
            else if (level >= 20 && level < 30) {
                return "Class C";
            }
            else if (level >= 30 && level < 40) {
                return "Steel Warrior Class C";
            }

            else if (level >= 40 && level < 50) {
                return "Class B";
            }
            else if (level >= 50 && level < 60) {
                return "Gold Warrior Class B";
            }
            else if (level >= 60 && level < 70) {
                return "Class A";
            }
            else if (level >= 70 && level < 80) {
                return "Titan Class A";
            }
            else if (level >= 80 && level < 90) {
                return "Class S";
            }
            else {
                return "Monarch Class S";
            }
        }





        const objectId = "664632b48435b33dc80620e0";

        let item = await Xp.findById(objectId);
        const penalties = getPenalties(gymXp, todoXp, dietXp, socialXp);
        try {

            if (item) {
                if (gymXp === -5 || todoXp === -5 || dietXp === -5 || socialXp === -5) {
                    if (gymXp == -5) {

                        item.gymXp += gymXp - 20;

                    }
                    if (todoXp == -5) {

                        item.todoXp += todoXp - 20;


                    }
                    if (dietXp == -5) {

                        item.dietXp += dietXp - 20;


                    }
                    if (socialXp == -5) {

                        item.socialXp += socialXp - 20;


                    }

                    let fullTotalXp = item.gymXp + item.todoXp + item.dietXp + item.socialXp;
                    item.totalXp = fullTotalXp;
                    const rewards = getReward(fullTotalXp);

                    const currentlevel = getCurrentLevel(fullTotalXp);
                    const titlell = getTitle(getCurrentLevel(fullTotalXp));
                    item.title = titlell;
                    item.currentlevel = currentlevel;
                    item.rewards = rewards;
                    item.penalties = penalties;

                    // Save the updated document
                    await item.save();

                    // Send a success response
                    return res.status(200).json(item);
                }
                else {

                    item.gymXp += gymXp;
                    item.todoXp += todoXp;
                    item.dietXp += dietXp;
                    item.socialXp += socialXp;
                    item.totalXp += totalXp;
                    let fullTotalXp = item.totalXp;
                    const rewards = getReward(fullTotalXp);

                    const currentlevel = getCurrentLevel(fullTotalXp);
                    const titlell = getTitle(getCurrentLevel(fullTotalXp));
                    item.title = titlell;
                    item.currentlevel = currentlevel;
                    item.rewards = rewards;
                    item.penalties = penalties;

                    // Save the updated document
                    await item.save();

                    // Send a success response
                    return res.status(200).json(item);
                }
            } else {
                console.log("Item not found");
            }

        }
        catch (err) {
            console.error(err);
        }
    }
    catch (error) {
        // If an error occurs, send an error response
        console.error('Error saving/updating XP data:', error);
        return res.status(500).json({ error: 'Internal Server Error' });
    }


});

app.post('/datexp', async (req, res) => {

    try {
        const { gymXp, todoXp, dietXp, socialXp } = req.body;
        const objectId = "664632b48435b33dc80620e0";

        let item = await Xp.findById(objectId);

        // Get the current date in "dd-mm-yyyy" format
        const now = new Date();

        const day = String(now.getDate()).padStart(2, '0');
        const month = String(now.getMonth() + 1).padStart(2, '0'); // January is 0!
        const year = now.getFullYear();
        const dater = `${day}-${month}-${year}`;
        //    console.log(dater);
        const totalXp = gymXp + todoXp + dietXp + socialXp;
        const getCurrentLevel = (totxp) => {
            const xpPerLevel = 100;

            // Calculate the current level
            const level = Math.floor(totxp / xpPerLevel);

            return level;

        }
        const getPenalties = (gymXp, todoXp, dietXp, socialXp) => {

            if (gymXp === -5 || todoXp === -5 || dietXp === -5 || socialXp === -5) {

                const randomNumber = Math.random();
                min = Math.ceil(1);
                max = Math.floor(3);
                const rand = Math.floor(randomNumber * (3)) + min;
                if (rand === 1) {
                    return "No social media for 2 days, full focus mode";
                }
                else if (rand === 2) {
                    return "No hearing songs for 2 days";
                }
                else if (rand === 3) {
                    return "Solve Leetcode 10 medium-level problems";
                }
            }
            else {
                return "No Penalties Till Now";
            }


        }
        const penalties = getPenalties(gymXp, todoXp, dietXp, socialXp);
        const getTitle = (level) => {
            if (level < 10) {
                return "Beginner";
            }
            else if (level >= 10 && level < 20) {
                return "Iron Warrior";
            }
            else if (level >= 20 && level < 30) {
                return "Class C";
            }
            else if (level >= 30 && level < 40) {
                return "Steel Warrior Class C";
            }

            else if (level >= 40 && level < 50) {
                return "Class B";
            }
            else if (level >= 50 && level < 60) {
                return "Gold Warrior Class B";
            }
            else if (level >= 60 && level < 70) {
                return "Class A";
            }
            else if (level >= 70 && level < 80) {
                return "Titan Class A";
            }
            else if (level >= 80 && level < 90) {
                return "Class S";
            }
            else {
                return "Monarch Class S";
            }
        }


        const getReward = (totxp) => {
            if (getCurrentLevel(totxp) % 3 === 0 && getCurrentLevel(totxp) !== 0) {

                const randomNumber = Math.random();
                min = Math.ceil(1);
                max = Math.floor(3);
                const rand = Math.floor(randomNumber * (3)) + min;
                if (rand === 1) {
                    return "Watching Netflix Series";
                }
                else if (rand === 2) {
                    return "Hanging out with friends";
                }
                else if (rand === 3) {
                    return "Buying Good clothes";
                }
            }
            else {
                return "No Rewards Right Now";
            }
        }



        const existingXP = await Xp.findOne({ dater });

        if (existingXP) {
            // If a document exists, update its values


            existingXP.gymXp = gymXp;
            existingXP.todoXp = todoXp;
            existingXP.dietXp = dietXp;
            existingXP.socialXp = socialXp;

            existingXP.totalXp = totalXp;


            existingXP.currentlevel = item.currentlevel;
            existingXP.rewards = item.rewards;
            existingXP.title = item.title;
            existingXP.penalties = penalties;

            // Save the updated document
            await existingXP.save();

            // Send a success response
            return res.status(200).json(existingXP);
        } else if (!existingXP) {
            const rewards = item.rewards;
            const title = item.title;
            // If no document exists, create a new one

            const currentlevel = item.currentlevel;
            const newXP = new Xp({
                gymXp,
                todoXp,
                dietXp,
                socialXp,
                title,
                currentlevel,
                totalXp,
                dater,
                rewards,
                penalties
            });


            // Save the new document
            await newXP.save();

            // Send a success response
            return res.status(201).json(newXP);
        }
    }

    catch (error) {
        // If an error occurs, send an error response
        console.error('Error saving/updating XP data:', error);
        return res.status(500).json({ error: 'Internal Server Error' });
    }
});
app.listen(port, () => {
    console.log(`Example app listening on port ${port}`);
});