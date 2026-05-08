import javax.swing.*;
import java.awt.*;

public class DeepExplanation extends JFrame { // Inheritance: This class IS a Frame

    public DeepExplanation() {
        // 1. Setting up the Window (JFrame)
        setTitle("I am the JFrame (The House)");
        setSize(400, 300);
        setLayout(new FlowLayout()); // Defining the Layout

        // 2. Creating a JPanel (The Room)
        // We use this to group these specific buttons together
        JPanel panel = new JPanel();
        panel.setBackground(Color.LIGHT_GRAY); // So you can see the panel's area
        
        // 3. Creating Components (The Atoms)
        JButton btn1 = new JButton("Button 1");
        JButton btn2 = new JButton("Button 2");

        // 4. Using the add() method
        panel.add(btn1); // Putting buttons into the Panel
        panel.add(btn2);
        
        this.add(panel); // Putting the Panel into the Frame

        // 5. Making it visible
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setVisible(true);

        // 6. Creating a JDialog (The Pop-up)
        JDialog dialog = new JDialog(this, "I am a JDialog");
        dialog.add(new JLabel("I have no min/max buttons!"));
        dialog.setSize(200, 100);
        dialog.setLocationRelativeTo(null); // Center it
        dialog.setVisible(true);
    }

    public static void main(String[] args) {
        new DeepExplanation();
    }
}