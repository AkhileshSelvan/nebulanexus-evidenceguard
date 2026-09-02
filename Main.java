import java.util.Scanner;

class Product {
    public double price;

    Product(double price) {
        this.price = price;
    }
}

class DiscountedProduct extends Product {
    private double discountRate;

    DiscountedProduct(double price, double discountRate) {
        super(price);
        this.discountRate = discountRate;
    }

    public void calculateSellingPrice() {
        if (discountRate > 1) {
            System.out.println("Not applicable");
        } else {
            double sellingPrice = price * (1 - discountRate);
            System.out.printf("%.2f%n", sellingPrice);
        }
    }
}

public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        double p = sc.nextDouble();
        double d = sc.nextDouble();

        DiscountedProduct product = new DiscountedProduct(p, d);
        product.calculateSellingPrice();

        sc.close();
    }
}
